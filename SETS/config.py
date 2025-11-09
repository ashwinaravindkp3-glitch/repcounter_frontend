# config.py
import pathlib
from datetime import datetime

# Hardware
SERIAL_PORT = 'COM5'
BAUD_RATE = 115200
TIMEOUT = 0.5

# Application
DATA_DIR = pathlib.Path("user_data")
DATA_DIR.mkdir(exist_ok=True)

# Dumbbell exercises
EXERCISES = [
    {"id": "bicep_curl", "name": "Bicep Curl", "icon": "💪", "calories_per_rep": 0.5},
    {"id": "shoulder_press", "name": "Seated Shoulder Press", "icon": "🏋️", "calories_per_rep": 0.7},
    {"id": "lateral_raise", "name": "Lateral Raise", "icon": "💥", "calories_per_rep": 0.6}
]

# RFID Users (move to CSV later)
RFID_USERS = {
    "7D133721": "John",
    "00000000": "Sarah",
}

# Web Server
HOST = '127.0.0.1'
PORT = 5000