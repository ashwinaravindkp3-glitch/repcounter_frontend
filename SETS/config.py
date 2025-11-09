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

# Simplified: Only 3 exercises
EXERCISES = ["Push-ups", "Squats", "Planks"]

# RFID Users (move to CSV later)
RFID_USERS = {
    "7D133721": "John",
    "00000000": "Sarah",
}

# Web Server
HOST = '127.0.0.1'
PORT = 5000