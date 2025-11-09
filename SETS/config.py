# config.py
import pathlib
from datetime import datetime

# Hardware
SERIAL_PORT = 'COM5'
BAUD_RATE = 115200
TIMEOUT = 0.5

# MCU Communication Delays (in seconds)
# Increase these if your MCU is slower or experiencing buffer overflow
MCU_INIT_DELAY = 3.0        # Wait after serial connection (MCU reset time)
MCU_MSG_DELAY = 0.2         # Minimum delay between messages (200ms)
MCU_SEND_DELAY = 0.15       # Delay after sending message (150ms)
POLLING_INTERVAL = 0.1      # How often to check for messages (100ms)

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
HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 5000
DISPLAY_URL = 'localhost'  # User-friendly display name

# Cache busting
import time
CACHE_VERSION = int(time.time())  # Unix timestamp for cache busting