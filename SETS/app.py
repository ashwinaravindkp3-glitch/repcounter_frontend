# app.py
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import threading
from datetime import datetime
from config import HOST, PORT, EXERCISES
from serial_handler import SerialHandler
from rfid_auth import RFIDAuth
from database import UserDatabase
import pathlib

app = Flask(__name__)
app.secret_key = 'fitness_tracker_secret'

# Disable all caching (force fresh load every time)
@app.after_request
def add_header(response):
    """Add headers to prevent caching"""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# Inject cache version into all templates
@app.context_processor
def inject_cache_version():
    """Make cache version available to all templates"""
    from config import CACHE_VERSION
    return dict(v=CACHE_VERSION)

# Global components (initialized in main.py)
serial_handler = None
rfid_auth = None
database = None

# Workout state
workout_state = {
    'active': False,
    'exercise': '',
    'exerciseName': '',
    'icon': '',
    'caloriesPerRep': 0,
    'targetReps': 0,
    'totalSets': 0,
    'currentSet': 1,
    'currentReps': 0,
    'totalCalories': 0,
    'startTime': None,
    'status': 'waiting',  # waiting, ready, active, completed
    'validReps': 0
}

# OLED selection tracking (for hybrid mode)
# User can select on OLED, frontend syncs in real-time
oled_selection = {
    'exercise': None,
    'exerciseName': None,
    'icon': None,
    'caloriesPerRep': 0,
    'reps': None,
    'sets': None
}

@app.route('/')
def index():
    if rfid_auth and rfid_auth.get_current_user():
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if not rfid_auth:
        return redirect(url_for('index'))

    user = rfid_auth.get_current_user()
    if not user:
        return redirect(url_for('index'))

    try:
        stats = database.get_total_stats(user)
    except Exception as e:
        print(f"Error getting stats: {e}")
        stats = {"total_workouts": 0, "total_reps": 0, "avg_accuracy": 0}

    return render_template('dashboard.html',
                          username=user,
                          stats=stats,
                          exercises=EXERCISES)

@app.route('/select_workout')
def select_workout():
    if not rfid_auth or not rfid_auth.get_current_user():
        return redirect(url_for('index'))
    return render_template('select_workout.html')

@app.route('/workout_monitor')
def workout_monitor():
    if not rfid_auth or not rfid_auth.get_current_user():
        return redirect(url_for('index'))
    if not workout_state['active']:
        return redirect(url_for('dashboard'))
    return render_template('workout_monitor.html')

@app.route('/history')
def history():
    if not rfid_auth:
        return redirect(url_for('index'))

    user = rfid_auth.get_current_user()
    if not user:
        return redirect(url_for('index'))

    try:
        history_data = database.get_workout_history(user)
        # Reverse to show newest first
        history_data.reverse()
    except Exception as e:
        print(f"Error getting history: {e}")
        history_data = []

    return render_template('history.html',
                          username=user,
                          history=history_data)

@app.route('/api/serial_status')
def serial_status():
    try:
        return jsonify({
            "connected": serial_handler.is_running if serial_handler else False,
            "current_user": rfid_auth.get_current_user() if rfid_auth else None
        })
    except Exception as e:
        print(f"Error in serial_status: {e}")
        return jsonify({
            "connected": False,
            "current_user": None
        })

@app.route('/api/start_workout', methods=['POST'])
def start_workout():
    """Start a new workout session"""
    if not rfid_auth or not rfid_auth.get_current_user():
        return jsonify({"error": "Not logged in"}), 401

    data = request.json
    exercise_id = data.get('exercise')
    reps = int(data.get('reps', 0))
    sets = int(data.get('sets', 0))

    # Find exercise details
    exercise_data = next((ex for ex in EXERCISES if ex['id'] == exercise_id), None)
    if not exercise_data:
        return jsonify({"error": "Invalid exercise"}), 400

    # Reset workout state
    workout_state.update({
        'active': True,
        'exercise': exercise_id,
        'exerciseName': exercise_data['name'],
        'icon': exercise_data['icon'],
        'caloriesPerRep': exercise_data['calories_per_rep'],
        'targetReps': reps,
        'totalSets': sets,
        'currentSet': 1,
        'currentReps': 0,
        'totalCalories': 0,
        'startTime': datetime.now(),
        'status': 'waiting',
        'validReps': 0
    })

    # Send workout config to MCU
    # Format: WORKOUT_START|exercise_id|reps|sets
    if serial_handler:
        message = f"WORKOUT_START|{exercise_id}|{reps}|{sets}\n"
        serial_handler.send_message(message)
        print(f"→ Sent to MCU: {message.strip()}")

    return jsonify({"success": True})

@app.route('/api/workout_status')
def get_workout_status():
    """Get current workout state"""
    return jsonify(workout_state)

@app.route('/api/workout_updates')
def get_workout_updates():
    """Poll for real-time workout updates"""
    return jsonify({
        'status': workout_state['status'],
        'reps': workout_state['currentReps'],
        'currentSet': workout_state['currentSet'],
        'calories': workout_state['totalCalories'],
        'totalReps': workout_state['currentReps'],
        'validReps': workout_state['validReps']
    })

@app.route('/api/cancel_workout', methods=['POST'])
def cancel_workout():
    """Cancel current workout"""
    workout_state['active'] = False

    # Send cancel to MCU
    if serial_handler:
        serial_handler.send_message("WORKOUT_CANCEL\n")

    return jsonify({"success": True})

@app.route('/api/oled_selection')
def get_oled_selection():
    """Get current OLED selections (for frontend sync)"""
    return jsonify(oled_selection)

@app.route('/api/send_frontend_selection', methods=['POST'])
def send_frontend_selection():
    """Send frontend selection to MCU/OLED display"""
    if not serial_handler:
        return jsonify({"error": "Serial not connected"}), 503

    data = request.json
    selection_type = data.get('type')  # 'exercise', 'reps', 'sets'
    value = data.get('value')

    # Send to MCU so OLED can display it
    if selection_type == 'exercise':
        message = f"WEB_EXERCISE|{value}\n"
        serial_handler.send_message(message)
        print(f"→ Web selected exercise: {value}")
    elif selection_type == 'reps':
        message = f"WEB_REPS|{value}\n"
        serial_handler.send_message(message)
        print(f"→ Web selected reps: {value}")
    elif selection_type == 'sets':
        message = f"WEB_SETS|{value}\n"
        serial_handler.send_message(message)
        print(f"→ Web selected sets: {value}")

    return jsonify({"success": True})

@app.route('/api/logout')
def logout():
    if rfid_auth:
        rfid_auth.logout()

    # Cancel any active workout
    workout_state['active'] = False

    # Reset OLED selection
    oled_selection.update({
        'exercise': None,
        'exerciseName': None,
        'icon': None,
        'caloriesPerRep': 0,
        'reps': None,
        'sets': None
    })

    return redirect(url_for('index'))

def update_workout_state(status=None, reps=None, current_set=None, valid_reps=None, calories=None):
    """Helper function to update workout state from main.py"""
    if status is not None:
        workout_state['status'] = status
    if reps is not None:
        workout_state['currentReps'] = reps
    if current_set is not None:
        workout_state['currentSet'] = current_set
    if valid_reps is not None:
        workout_state['validReps'] = valid_reps
    if calories is not None:
        workout_state['totalCalories'] = calories

def complete_workout():
    """Mark workout as completed"""
    workout_state['status'] = 'completed'
    workout_state['active'] = False

def run_flask():
    """Run Flask in a separate thread"""
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False, threaded=True)
