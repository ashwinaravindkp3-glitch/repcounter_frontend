# main.py
from config import SERIAL_PORT, BAUD_RATE, TIMEOUT, RFID_USERS, PORT, EXERCISES
from serial_handler import SerialHandler
from rfid_auth import RFIDAuth
from database import UserDatabase
from datetime import datetime
import pathlib
import threading
import time
import app as flask_app

def main():
    # Initialize components
    flask_app.database = UserDatabase(pathlib.Path("user_data"))
    flask_app.rfid_auth = RFIDAuth(RFID_USERS)
    flask_app.serial_handler = SerialHandler(SERIAL_PORT, BAUD_RATE, TIMEOUT)

    # Store references for easy access
    global serial_handler, rfid_auth, database
    serial_handler = flask_app.serial_handler
    rfid_auth = flask_app.rfid_auth
    database = flask_app.database

    # Start Flask in background thread
    print("🚀 Starting Flask server...")
    flask_thread = threading.Thread(target=flask_app.run_flask, daemon=True)
    flask_thread.start()
    time.sleep(1)

    # Start serial communication
    print(f"📡 Connecting to {SERIAL_PORT}...")
    if not serial_handler.start():
        print("✗ Failed to start serial. Running in web-only mode...")
        print(f"📊 Open browser: http://127.0.0.1:{PORT}")
        # Keep running for web interface
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Shutting down...")
        return

    print(f"✓ Serial connected: {SERIAL_PORT} @ {BAUD_RATE}")
    print(f"📊 Open browser: http://127.0.0.1:{PORT}")
    print("\n" + "="*50)
    print("SmartDumbbell System Running!")
    print("="*50 + "\n")

    # Main serial processing loop
    try:
        while True:
            message = serial_handler.get_message()
            if message:
                handle_serial_message(message)
            time.sleep(0.05)  # Poll faster for better responsiveness
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    finally:
        serial_handler.stop()

def handle_serial_message(message: str):
    """Process messages from MCU"""
    print(f"← MCU: {message}")

    # ==========================================
    # RFID Login
    # ==========================================
    # Format from MCU: UID_REQ|7D133721 AB CD EF
    uid = rfid_auth.parse_uid_message(message)
    if uid:
        is_valid, username = rfid_auth.login(uid)
        if is_valid:
            serial_handler.send_message(f"USER_OK|{username}\n")
            print(f"✅ User logged in: {username}")
        else:
            serial_handler.send_message("USER_FAIL\n")
            print(f"❌ Invalid RFID card")
        return

    # ==========================================
    # Workout Status Updates
    # ==========================================
    # Format from MCU: STATUS|waiting (or ready, or active)
    if message.startswith("STATUS|"):
        status = message.split('|')[1].strip()
        flask_app.update_workout_state(status=status)
        print(f"📊 Workout status: {status}")
        return

    # ==========================================
    # Rep Count Update
    # ==========================================
    # Format from MCU: REP_COUNT|5
    if message.startswith("REP_COUNT|"):
        try:
            reps = int(message.split('|')[1])
            # Calculate calories
            calories = reps * flask_app.workout_state['caloriesPerRep']
            flask_app.update_workout_state(reps=reps, calories=calories)
            print(f"🏋️ Rep count: {reps} | Calories: {calories:.1f}")
        except (ValueError, IndexError) as e:
            print(f"⚠️ Invalid REP_COUNT message: {e}")
        return

    # ==========================================
    # Set Progress Update
    # ==========================================
    # Format from MCU: SET_PROGRESS|2
    if message.startswith("SET_PROGRESS|"):
        try:
            current_set = int(message.split('|')[1])
            flask_app.update_workout_state(current_set=current_set)
            print(f"📈 Current set: {current_set}")
        except (ValueError, IndexError) as e:
            print(f"⚠️ Invalid SET_PROGRESS message: {e}")
        return

    # ==========================================
    # Calorie Update (if MCU calculates it)
    # ==========================================
    # Format from MCU: CALORIES|45.5
    if message.startswith("CALORIES|"):
        try:
            calories = float(message.split('|')[1])
            flask_app.update_workout_state(calories=calories)
            print(f"🔥 Calories burned: {calories:.1f}")
        except (ValueError, IndexError) as e:
            print(f"⚠️ Invalid CALORIES message: {e}")
        return

    # ==========================================
    # Workout Completion
    # ==========================================
    # Format from MCU: WORKOUT_COMPLETE|exercise|reps|sets|duration|valid_reps
    # Example: WORKOUT_COMPLETE|bicep_curl|10|3|5.2|28
    if message.startswith("WORKOUT_COMPLETE|"):
        try:
            parts = message.split('|')
            if len(parts) >= 6:
                username = rfid_auth.get_current_user()
                if username:
                    exercise_id = parts[1]
                    reps = int(parts[2])
                    sets = int(parts[3])
                    duration = float(parts[4])
                    valid_reps = int(parts[5])

                    # Find exercise name
                    exercise_data = next((ex for ex in EXERCISES if ex['id'] == exercise_id), None)
                    exercise_name = exercise_data['name'] if exercise_data else exercise_id

                    # Save to database
                    database.record_workout(
                        username=username,
                        exercise=exercise_name,
                        reps=reps,
                        sets=sets,
                        duration=duration,
                        valid_reps=valid_reps
                    )

                    # Update workout state
                    flask_app.update_workout_state(valid_reps=valid_reps)
                    flask_app.complete_workout()

                    print(f"💾 Workout saved for {username}")
                    print(f"   Exercise: {exercise_name}")
                    print(f"   Reps: {reps} × {sets} = {reps * sets} total")
                    print(f"   Valid reps: {valid_reps} ({valid_reps / (reps * sets) * 100:.0f}%)")
                    print(f"   Duration: {duration:.1f} min")
        except (ValueError, IndexError) as e:
            print(f"⚠️ Invalid WORKOUT_COMPLETE message: {e}")
        return

    # ==========================================
    # Position Status (for starting position)
    # ==========================================
    # Format from MCU: POSITION|at_start (or moving_to_start)
    if message.startswith("POSITION|"):
        position = message.split('|')[1].strip()
        if position == "at_start":
            flask_app.update_workout_state(status='ready')
            print(f"✅ User at starting position")
        else:
            flask_app.update_workout_state(status='waiting')
            print(f"⏳ Moving to starting position...")
        return

    # ==========================================
    # Debug/Unknown Messages
    # ==========================================
    print(f"ℹ️ Unhandled message: {message}")

if __name__ == "__main__":
    main()
