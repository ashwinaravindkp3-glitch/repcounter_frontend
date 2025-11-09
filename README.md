# SmartDumbbell - Advanced Rep Counter System

An advanced IoT-based dumbbell rep counter with RFID authentication and real-time workout tracking.

## Features

- **RFID Authentication**: Secure login via RFID card scanning
- **Real-time Rep Counting**: Live tracking of reps, sets, and calories
- **Beautiful Animations**: Modern, animated UI with smooth transitions
- **Workout History**: Track your progress over time
- **3 Dumbbell Exercises**:
  - Bicep Curl 💪
  - Seated Shoulder Press 🏋️
  - Lateral Raise 💥

## System Architecture

```
┌─────────────┐         Serial         ┌─────────────┐
│             │◄─────────────────────►│             │
│  Frontend   │     (115200 baud)      │     MCU     │
│  (Flask)    │                        │  (Arduino)  │
│             │                        │             │
└─────────────┘                        └─────────────┘
       │                                      │
       │                                      │
       ▼                                      ▼
  Web Browser                          RFID + MPU6050
  (Dashboard)                         (Sensors)
```

## Installation

### 1. Install Python Dependencies

```bash
cd SETS
pip install -r requirements.txt
```

### 2. Configure Serial Port

Edit `config.py` and set your COM port:

```python
SERIAL_PORT = 'COM5'  # Windows: COM5, Linux: /dev/ttyUSB0
BAUD_RATE = 115200
```

### 3. Add RFID Users

Edit `config.py` to add your RFID cards:

```python
RFID_USERS = {
    "7D133721": "John",
    "00000000": "Sarah",
}
```

### 4. Run the System

```bash
cd SETS
python main.py
```

Open browser to: **http://127.0.0.1:5000**

## MCU Communication Protocol

### Messages FROM Frontend TO MCU

#### 1. User Authentication Response
```
USER_OK|<username>
```
Sent after successful RFID validation.
Example: `USER_OK|John`

```
USER_FAIL
```
Sent after failed RFID validation.

#### 2. Workout Start
```
WORKOUT_START|<exercise_id>|<reps>|<sets>
```
Sent when user starts a workout.
Example: `WORKOUT_START|bicep_curl|10|3`

Exercise IDs:
- `bicep_curl`
- `shoulder_press`
- `lateral_raise`

#### 3. Workout Cancel
```
WORKOUT_CANCEL
```
Sent when user cancels the workout.

---

### Messages FROM MCU TO Frontend

#### 1. RFID Login Request
```
UID_REQ|<uid_with_spaces>
```
Sent when RFID card is scanned.
Example: `UID_REQ|7D 13 37 21 AB CD EF 00`

#### 2. Workout Status
```
STATUS|<status>
```
Status values:
- `waiting` - User needs to move to starting position
- `ready` - User at starting position, can begin
- `active` - Workout in progress

Example: `STATUS|waiting`

#### 3. Position Status
```
POSITION|<position>
```
Position values:
- `at_start` - User is at starting position
- `moving_to_start` - User is moving to position

Example: `POSITION|at_start`

#### 4. Rep Count Update
```
REP_COUNT|<current_reps>
```
Sent after each rep is detected.
Example: `REP_COUNT|5`

#### 5. Set Progress
```
SET_PROGRESS|<current_set>
```
Sent when moving to next set.
Example: `SET_PROGRESS|2`

#### 6. Calorie Update (Optional)
```
CALORIES|<total_calories>
```
If MCU calculates calories, send this.
Example: `CALORIES|45.5`

Note: Frontend also calculates calories based on exercise type.

#### 7. Workout Complete
```
WORKOUT_COMPLETE|<exercise_id>|<reps>|<sets>|<duration>|<valid_reps>
```
Sent when all sets are completed.
Example: `WORKOUT_COMPLETE|bicep_curl|10|3|5.2|28`

Parameters:
- `exercise_id`: Exercise identifier
- `reps`: Reps per set
- `sets`: Total sets
- `duration`: Total time in minutes (float)
- `valid_reps`: Number of reps with proper form

---

## Example MCU Workflow

### 1. User Login
```
MCU → Frontend: UID_REQ|7D 13 37 21 AB
Frontend → MCU: USER_OK|John
```

### 2. Start Workout
```
Frontend → MCU: WORKOUT_START|bicep_curl|10|3
MCU → Frontend: STATUS|waiting
MCU → Frontend: POSITION|moving_to_start
```

### 3. User Reaches Starting Position
```
MCU → Frontend: POSITION|at_start
MCU → Frontend: STATUS|ready
```

### 4. Workout in Progress
```
MCU → Frontend: STATUS|active
MCU → Frontend: REP_COUNT|1
MCU → Frontend: REP_COUNT|2
...
MCU → Frontend: REP_COUNT|10
MCU → Frontend: SET_PROGRESS|2
```

### 5. Workout Complete
```
MCU → Frontend: WORKOUT_COMPLETE|bicep_curl|10|3|5.2|28
```

---

## User Workflow

1. **Scan RFID Card** → Login screen
2. **View Dashboard** → See stats and exercise options
3. **Select Exercise** → Choose from 3 dumbbell exercises
4. **Configure Workout** → Select reps and sets
5. **Start Workout** → Move to starting position
6. **Perform Reps** → Real-time tracking on screen
7. **Complete Workout** → View summary and calories burned
8. **Check History** → Review past performance

---

## File Structure

```
repcounter_frontend/
└── SETS/
    ├── main.py              # Main entry point
    ├── app.py               # Flask routes and API
    ├── config.py            # Configuration
    ├── serial_handler.py    # Serial communication
    ├── rfid_auth.py         # RFID authentication
    ├── database.py          # User data storage
    ├── requirements.txt     # Python dependencies
    ├── static/
    │   ├── css/
    │   │   └── main.css     # Animated styles
    │   └── js/
    └── templates/
        ├── login.html       # RFID login page
        ├── dashboard.html   # Main dashboard
        ├── select_workout.html  # Rep/Sets selection
        ├── workout_monitor.html # Real-time workout
        └── history.html     # Workout history
```

---

## Configuration Options

### Serial Settings (`config.py`)
```python
SERIAL_PORT = 'COM5'  # Change to your port
BAUD_RATE = 115200
TIMEOUT = 0.5
```

### Web Server Settings (`config.py`)
```python
HOST = '127.0.0.1'  # Localhost only
PORT = 5000
```

### Exercise Configuration (`config.py`)
```python
EXERCISES = [
    {"id": "bicep_curl", "name": "Bicep Curl", "icon": "💪", "calories_per_rep": 0.5},
    {"id": "shoulder_press", "name": "Seated Shoulder Press", "icon": "🏋️", "calories_per_rep": 0.7},
    {"id": "lateral_raise", "name": "Lateral Raise", "icon": "💥", "calories_per_rep": 0.6}
]
```

---

## Troubleshooting

### Serial Port Issues
- **Windows**: Check Device Manager for COM port number
- **Linux**: Grant permissions: `sudo usermod -a -G dialout $USER`
- **Mac**: Port usually `/dev/cu.usbserial-*`

### Web Interface Not Loading
- Check Flask is running: Look for "Running on http://127.0.0.1:5000"
- Try different port in `config.py`

### RFID Not Working
- Verify RFID UID in `config.py`
- Check serial monitor for `UID_REQ` messages
- Ensure proper message format with `|` separator

---

## Tech Stack

- **Backend**: Python 3.7+, Flask
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Communication**: PySerial (Serial UART)
- **Database**: CSV files (simple, portable)
- **Styling**: Custom CSS with animations

---

## License

MIT License - Feel free to use for your embedded projects!

---

## Credits

Built for embedded systems projects with focus on:
- Real-time communication
- Minimal frontend overhead
- MCU-driven logic
- Beautiful user experience

**Enjoy your workouts! 💪🏋️**
