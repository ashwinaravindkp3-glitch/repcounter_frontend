# main.py
from config import SERIAL_PORT, BAUD_RATE, TIMEOUT, RFID_USERS, PORT, EXERCISES, DISPLAY_URL
from serial_handler import SerialHandler
from rfid_auth import RFIDAuth
from database import UserDatabase
from datetime import datetime
import pathlib
import threading
import time
import app as flask_app

# Browser auto-launch
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

def launch_browser():
    """Auto-launch Chrome browser with Selenium"""
    if not SELENIUM_AVAILABLE:
        print("ℹ️ Selenium not available. Please open browser manually.")
        return None

    try:
        print("🌐 Launching Chrome browser...")
        chrome_options = Options()
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')

        # CACHE-BUSTING: Disable all caching
        chrome_options.add_argument('--disable-cache')
        chrome_options.add_argument('--disable-application-cache')
        chrome_options.add_argument('--disable-offline-load-stale-cache')
        chrome_options.add_argument('--disk-cache-size=0')
        chrome_options.add_argument('--incognito')  # Use incognito mode for fresh session

        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Try to create driver
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(f'http://{DISPLAY_URL}:{PORT}')
        print(f"✓ Browser opened: http://{DISPLAY_URL}:{PORT}")
        return driver
    except Exception as e:
        print(f"⚠️ Could not auto-launch browser: {e}")
        print(f"📊 Please open manually: http://{DISPLAY_URL}:{PORT}")
        return None

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
    time.sleep(2)  # Give Flask time to start

    # Auto-launch browser
    browser = launch_browser()

    # Start serial communication
    print(f"📡 Connecting to {SERIAL_PORT}...")
    if not serial_handler.start():
        print("✗ Failed to start serial. Running in web-only mode...")
        print(f"📊 URL: http://{DISPLAY_URL}:{PORT}")
        # Keep running for web interface
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Shutting down...")
            if browser:
                browser.quit()
        return

    print(f"✓ Serial connected: {SERIAL_PORT} @ {BAUD_RATE}")
    print(f"📊 URL: http://{DISPLAY_URL}:{PORT}")
    print("\n" + "="*50)
    print("🏋️ SETS - SmartDumbbell System Running!")
    print("="*50 + "\n")

    # Main serial processing loop
    # Slower polling to give MCU time to process
    try:
        while True:
            message = serial_handler.get_message()
            if message:
                handle_serial_message(message)

            # Poll every 100ms (MCU-friendly, prevents buffer overflow)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        if browser:
            browser.quit()
    finally:
        serial_handler.stop()

def handle_serial_message(message: str):
    """Process messages from MCU - Full Protocol Implementation"""

    # Filter out Arduino debug/display messages
    debug_keywords = [
        "→ Frontend:", "← RX:", "→", "←",
        "─────", "═════", "╔", "╚", "║",
        "All selections complete", "Press 'c' to confirm",
        "Press 'm' for menu", "Auto-demo complete",
        "TIP:", "Unknown command", "HYBRID MODE DEMONSTRATED",
        "DEMO SEQUENCE COMPLETE", "Frontend synchronized",
        "Exercise:", "Reps:", "Sets:", "OLED Display State"
    ]

    # Skip Arduino debug output
    if any(keyword in message for keyword in debug_keywords):
        return

    # Only print actual protocol messages
    protocol_messages = [
        "UID_REQ|", "USER_OK|", "USER_FAIL",
        "CFG_EXERCISE|", "CFG_REPS|", "CFG_SETS|",
        "CMD_EXERCISE|", "CMD_REPS|", "CMD_SETS|",
        "WORKOUT_START|", "WORKOUT_PAUSE|", "WORKOUT_RESUME|",
        "WORKOUT_STOP|", "WORKOUT_END|",
        "REP_DETECT|", "SET_COMPLETE|", "IMU_DATA|",
        "HEARTBEAT|", "PING", "PONG|", "ERROR|",
        # Legacy messages for backward compatibility
        "EXERCISE_SELECTED|", "REPS_SELECTED|", "SETS_SELECTED|",
        "WORKOUT_START_CONFIRMED", "STATUS|", "REP_COUNT|",
        "SET_PROGRESS|", "CALORIES|", "WORKOUT_COMPLETE|", "POSITION|"
    ]

    if any(message.startswith(protocol) for protocol in protocol_messages):
        print(f"← MCU: {message}")

    # ==========================================
    # A. AUTHENTICATION
    # ==========================================

    # UID_REQ|7D 13 37 21 78
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
    # B. WORKOUT CONFIGURATION SYNC
    # ==========================================

    # CFG_EXERCISE|1|Squats
    if message.startswith("CFG_EXERCISE|"):
        try:
            parts = message.split('|')
            exercise_id = int(parts[1])
            exercise_name = parts[2] if len(parts) > 2 else ""

            # Map exercise ID to our system
            exercise_map = {
                0: "bicep_curl",
                1: "shoulder_press",  # Or map to squats if you have it
                2: "lateral_raise"     # Or map to overhead press
            }

            mapped_id = exercise_map.get(exercise_id, "bicep_curl")
            exercise_data = next((ex for ex in EXERCISES if ex['id'] == mapped_id), None)

            if exercise_data:
                flask_app.oled_selection.update({
                    'exercise': mapped_id,
                    'exerciseName': exercise_data['name'],
                    'icon': exercise_data['icon'],
                    'caloriesPerRep': exercise_data['calories_per_rep']
                })
                print(f"🎮 OLED: Exercise configured - {exercise_data['name']} (ID: {exercise_id})")
        except (ValueError, IndexError) as e:
            print(f"⚠️ Invalid CFG_EXERCISE message: {e}")
        return

    # CFG_REPS|15
    if message.startswith("CFG_REPS|"):
        try:
            reps = int(message.split('|')[1])
            flask_app.oled_selection['reps'] = reps
            print(f"🎮 OLED: Reps configured - {reps}")
        except (ValueError, IndexError) as e:
            print(f"⚠️ Invalid CFG_REPS message: {e}")
        return

    # CFG_SETS|3
    if message.startswith("CFG_SETS|"):
        try:
            sets = int(message.split('|')[1])
            flask_app.oled_selection['sets'] = sets
            print(f"🎮 OLED: Sets configured - {sets}")
        except (ValueError, IndexError) as e:
            print(f"⚠️ Invalid CFG_SETS message: {e}")
        return

    # ==========================================
    # C. WORKOUT CONTROL
    # ==========================================

    # WORKOUT_START|1|15|3|12345678
    if message.startswith("WORKOUT_START|"):
        try:
            parts = message.split('|')
            exercise_id = int(parts[1])
            reps = int(parts[2])
            sets = int(parts[3])
            mcu_timestamp = int(parts[4]) if len(parts) > 4 else 0

            # Map exercise ID
            exercise_map = {0: "bicep_curl", 1: "shoulder_press", 2: "lateral_raise"}
            mapped_id = exercise_map.get(exercise_id, "bicep_curl")
            exercise_data = next((ex for ex in EXERCISES if ex['id'] == mapped_id), None)

            if exercise_data:
                flask_app.workout_state.update({
                    'active': True,
                    'exercise': mapped_id,
                    'exerciseName': exercise_data['name'],
                    'icon': exercise_data['icon'],
                    'caloriesPerRep': exercise_data['calories_per_rep'],
                    'targetReps': reps,
                    'totalSets': sets,
                    'currentSet': 1,
                    'currentReps': 0,
                    'totalCalories': 0,
                    'startTime': datetime.now().isoformat(),
                    'mcuStartTimestamp': mcu_timestamp,
                    'status': 'active',
                    'validReps': 0
                })
                print(f"🚀 WORKOUT STARTED:")
                print(f"   Exercise: {exercise_data['name']}")
                print(f"   Target: {reps} reps × {sets} sets")
                print(f"   MCU Time: {mcu_timestamp}ms")
        except (ValueError, IndexError) as e:
            print(f"⚠️ Invalid WORKOUT_START message: {e}")
        return

    # WORKOUT_PAUSE|12389456
    if message.startswith("WORKOUT_PAUSE|"):
        try:
            mcu_timestamp = int(message.split('|')[1])
            flask_app.update_workout_state(status='paused')
            print(f"⏸️ Workout paused at {mcu_timestamp}ms")
        except (ValueError, IndexError) as e:
            print(f"⚠️ Invalid WORKOUT_PAUSE message: {e}")
        return

    # WORKOUT_RESUME|12401234
    if message.startswith("WORKOUT_RESUME|"):
        try:
            mcu_timestamp = int(message.split('|')[1])
            flask_app.update_workout_state(status='active')
            print(f"▶️ Workout resumed at {mcu_timestamp}ms")
        except (ValueError, IndexError) as e:
            print(f"⚠️ Invalid WORKOUT_RESUME message: {e}")
        return

    # WORKOUT_STOP|12567890
    if message.startswith("WORKOUT_STOP|"):
        try:
            mcu_timestamp = int(message.split('|')[1])
            flask_app.complete_workout()
            print(f"🛑 Workout stopped at {mcu_timestamp}ms")
        except (ValueError, IndexError) as e:
            print(f"⚠️ Invalid WORKOUT_STOP message: {e}")
        return

    # WORKOUT_END|12567890
    if message.startswith("WORKOUT_END|"):
        try:
            mcu_timestamp = int(message.split('|')[1])
            flask_app.complete_workout()
            print(f"✅ Workout completed at {mcu_timestamp}ms")
        except (ValueError, IndexError) as e:
            print(f"⚠️ Invalid WORKOUT_END message: {e}")
        return

    # ==========================================
    # D. REAL-TIME REP TRACKING
    # ==========================================

    # REP_DETECT|5|2|12350000
    if message.startswith("REP_DETECT|"):
        try:
            parts = message.split('|')
            rep_num = int(parts[1])
            set_num = int(parts[2])
            mcu_timestamp = int(parts[3]) if len(parts) > 3 else 0

            # Calculate calories
            calories = rep_num * flask_app.workout_state.get('caloriesPerRep', 0.5)

            flask_app.update_workout_state(
                reps=rep_num,
                current_set=set_num,
                calories=calories
            )
            print(f"🏋️ Rep {rep_num} of Set {set_num} at {mcu_timestamp}ms | Calories: {calories:.1f}")
        except (ValueError, IndexError) as e:
            print(f"⚠️ Invalid REP_DETECT message: {e}")
        return

    # SET_COMPLETE|2|15|12380000
    if message.startswith("SET_COMPLETE|"):
        try:
            parts = message.split('|')
            set_num = int(parts[1])
            total_reps = int(parts[2])
            mcu_timestamp = int(parts[3]) if len(parts) > 3 else 0

            flask_app.update_workout_state(current_set=set_num + 1, reps=0)
            print(f"📈 Set {set_num} complete: {total_reps} reps at {mcu_timestamp}ms")
        except (ValueError, IndexError) as e:
            print(f"⚠️ Invalid SET_COMPLETE message: {e}")
        return

    # IMU_DATA|Y|1.5|12345678 (optional - for debugging)
    if message.startswith("IMU_DATA|"):
        # This is optional - just log it if present
        try:
            parts = message.split('|')
            axis = parts[1]
            value = float(parts[2])
            mcu_timestamp = int(parts[3]) if len(parts) > 3 else 0
            # Just log, don't process
            # print(f"📊 IMU {axis}: {value}g at {mcu_timestamp}ms")
        except (ValueError, IndexError):
            pass
        return

    # ==========================================
    # E. SYSTEM STATUS
    # ==========================================

    # HEARTBEAT|12345678
    if message.startswith("HEARTBEAT|"):
        # Just acknowledge heartbeat, no action needed
        return

    # PING
    if message == "PING":
        serial_handler.send_message(f"PONG|{int(datetime.now().timestamp() * 1000)}\n")
        return

    # ERROR|E001|IMU initialization failed
    if message.startswith("ERROR|"):
        try:
            parts = message.split('|')
            error_code = parts[1]
            error_msg = parts[2] if len(parts) > 2 else "Unknown error"
            print(f"❌ MCU ERROR [{error_code}]: {error_msg}")
        except (ValueError, IndexError) as e:
            print(f"⚠️ Invalid ERROR message: {e}")
        return

    # ==========================================
    # HYBRID: Exercise Selection from OLED
    # ==========================================
    # Format from MCU: EXERCISE_SELECTED|exercise_id
    # Example: EXERCISE_SELECTED|bicep_curl
    # User chose exercise on OLED, frontend will sync and show it
    if message.startswith("EXERCISE_SELECTED|"):
        try:
            exercise_id = message.split('|')[1].strip()
            exercise_data = next((ex for ex in EXERCISES if ex['id'] == exercise_id), None)
            if exercise_data:
                flask_app.oled_selection.update({
                    'exercise': exercise_id,
                    'exerciseName': exercise_data['name'],
                    'icon': exercise_data['icon'],
                    'caloriesPerRep': exercise_data['calories_per_rep']
                })
                print(f"🎮 OLED: User selected {exercise_data['name']}")
                print(f"   Frontend will update in real-time!")
            else:
                print(f"⚠️ Unknown exercise ID: {exercise_id}")
        except (ValueError, IndexError) as e:
            print(f"⚠️ Invalid EXERCISE_SELECTED message: {e}")
        return

    # ==========================================
    # HYBRID: Reps Selection from OLED
    # ==========================================
    # Format from MCU: REPS_SELECTED|10
    # User chose reps on OLED, frontend will sync
    if message.startswith("REPS_SELECTED|"):
        try:
            reps = int(message.split('|')[1])
            flask_app.oled_selection['reps'] = reps
            print(f"🎮 OLED: User selected {reps} reps")
        except (ValueError, IndexError) as e:
            print(f"⚠️ Invalid REPS_SELECTED message: {e}")
        return

    # ==========================================
    # HYBRID: Sets Selection from OLED
    # ==========================================
    # Format from MCU: SETS_SELECTED|3
    # User chose sets on OLED, frontend will sync
    if message.startswith("SETS_SELECTED|"):
        try:
            sets = int(message.split('|')[1])
            flask_app.oled_selection['sets'] = sets
            print(f"🎮 OLED: User selected {sets} sets")
        except (ValueError, IndexError) as e:
            print(f"⚠️ Invalid SETS_SELECTED message: {e}")
        return

    # ==========================================
    # HYBRID: Workout Start Confirmation
    # ==========================================
    # Format from MCU: WORKOUT_START_CONFIRMED
    # This happens when ALL selections are complete (from either OLED or Frontend)
    # and user confirms "START" on OLED or Frontend
    if message.startswith("WORKOUT_START_CONFIRMED"):
        # Check if we have all required data (from OLED selections or Frontend)
        oled = flask_app.oled_selection

        # Use OLED selections if available, otherwise use what's already in workout_state
        exercise_id = oled.get('exercise') or flask_app.workout_state.get('exercise')
        reps = oled.get('reps') or flask_app.workout_state.get('targetReps')
        sets = oled.get('sets') or flask_app.workout_state.get('totalSets')

        if exercise_id and reps and sets:
            exercise_data = next((ex for ex in EXERCISES if ex['id'] == exercise_id), None)
            if exercise_data:
                flask_app.workout_state.update({
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
                    'startTime': datetime.now().isoformat(),
                    'status': 'waiting',
                    'validReps': 0
                })
                print(f"🚀 WORKOUT STARTED:")
                print(f"   Exercise: {exercise_data['name']}")
                print(f"   Target: {reps} reps × {sets} sets")
                print(f"   Both OLED & Frontend synchronized!")
            else:
                print(f"⚠️ Unknown exercise: {exercise_id}")
        else:
            print(f"⚠️ Missing workout parameters (exercise/reps/sets)")
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
    # Debug/Unknown Messages (filtered - no spam)
    # ==========================================
    # Silently ignore unrecognized messages to keep console clean

if __name__ == "__main__":
    main()
