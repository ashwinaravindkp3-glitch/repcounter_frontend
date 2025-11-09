# main.py
from config import SERIAL_PORT, BAUD_RATE, TIMEOUT, RFID_USERS, PORT
from serial_handler import SerialHandler
from rfid_auth import RFIDAuth
from database import UserDatabase
from app import app, serial_handler, rfid_auth, database, run_flask
import pathlib
import threading
import time

def main():
    global serial_handler, rfid_auth, database
    
    # Initialize components
    database = UserDatabase(pathlib.Path("user_data"))
    rfid_auth = RFIDAuth(RFID_USERS)
    serial_handler = SerialHandler(SERIAL_PORT, BAUD_RATE, TIMEOUT)
    
    # Start Flask in background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    time.sleep(1)
    
    # Start serial communication
    if not serial_handler.start():
        print("Failed to start serial. Exiting...")
        return
    
    print(f"🚀 Fitness Tracker Running!")
    print(f"📊 Open browser: http://127.0.0.1:{PORT}")
    print(f"📡 Serial: {SERIAL_PORT} @ {BAUD_RATE}")
    
    # Main serial processing loop
    try:
        while True:
            message = serial_handler.get_message()
            if message:
                handle_serial_message(message)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        serial_handler.stop()

def handle_serial_message(message: str):
    """Process messages from MCU"""
    print(f"← {message}")
    
    # RFID Login
    uid = rfid_auth.parse_uid_message(message)
    if uid:
        is_valid, username = rfid_auth.login(uid)
        if is_valid:
            serial_handler.send_message(f"USER_OK|{username}\n")
            print(f"✅ User logged in: {username}")
        else:
            serial_handler.send_message("USER_FAIL\n")
        return
    
    # Exercise Results (sent by MCU after workout)
    if message.startswith("RESULT|"):
        parts = message.split('|')
        if len(parts) == 6:
            username = rfid_auth.get_current_user()
            if username:
                # RESULT|<exercise>|<reps>|<sets>|<duration>|<valid_reps>
                database.record_workout(
                    username=username,
                    exercise=parts[1],
                    reps=int(parts[2]),
                    sets=int(parts[3]),
                    duration=float(parts[4]),
                    valid_reps=int(parts[5])
                )
                print(f"💾 Workout saved for {username}")

if __name__ == "__main__":
    main()