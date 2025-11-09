# app.py
from flask import Flask, render_template, request, jsonify, redirect, url_for
import threading
from config import HOST, PORT, EXERCISES
from serial_handler import SerialHandler
from rfid_auth import RFIDAuth
from database import UserDatabase
import pathlib

app = Flask(__name__)
app.secret_key = 'fitness_tracker_secret'

# Global components (initialized in main.py)
serial_handler = None
rfid_auth = None
database = None

@app.route('/')
def index():
    if rfid_auth.get_current_user():
        return redirect(url_for('dashboard'))
    return render_template('login.html', 
                          current_time=datetime.now().strftime("%I:%M %p"))

@app.route('/dashboard')
def dashboard():
    user = rfid_auth.get_current_user()
    if not user:
        return redirect(url_for('index'))
    
    stats = database.get_total_stats(user)
    return render_template('dashboard.html', 
                          username=user,
                          stats=stats,
                          exercises=EXERCISES)

@app.route('/history')
def history():
    user = rfid_auth.get_current_user()
    if not user:
        return redirect(url_for('index'))
    
    history = database.get_workout_history(user)
    return render_template('history.html', 
                          username=user,
                          history=history)

@app.route('/api/serial_status')
def serial_status():
    return jsonify({
        "connected": serial_handler.is_running if serial_handler else False,
        "current_user": rfid_auth.get_current_user()
    })

@app.route('/api/logout')
def logout():
    rfid_auth.logout()
    return redirect(url_for('index'))

def run_flask():
    """Run Flask in a separate thread"""
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)

# Template files will be created in templates/ folder