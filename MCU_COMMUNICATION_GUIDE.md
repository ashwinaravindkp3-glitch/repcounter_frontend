# MCU Communication Protocol Guide

## Overview

The SETS system uses **UART serial communication** (115200 baud) to exchange messages between the MCU (Arduino/ESP32) and the Python backend.

**Communication Format:** Plain text messages separated by newline (`\n`)

---

## Serial Settings

```
Baud Rate: 115200
Data Bits: 8
Parity: None
Stop Bits: 1
Flow Control: None
```

**Configuration in Python:** `SETS/config.py`
```python
SERIAL_PORT = 'COM5'  # Change to your port (COM5, /dev/ttyUSB0, etc.)
BAUD_RATE = 115200
```

---

## Message Protocol

### **From MCU → Python (Messages you send)**

All messages use pipe (`|`) as delimiter: `MESSAGE_TYPE|field1|field2|...`

#### 1. **RFID Authentication**
```
UID_REQ|7D133721
```
- **When:** User scans RFID card
- **Format:** `UID_REQ|<hex_uid>`
- **Example:** `UID_REQ|7D133721`
- **Response from Python:**
  - `USER_OK|John` (valid user)
  - `USER_FAIL` (invalid user)

#### 2. **Exercise Selection (OLED)**
```
EXERCISE_SELECTED|bicep_curl
```
- **When:** User selects exercise on OLED
- **Format:** `EXERCISE_SELECTED|<exercise_id>`
- **Options:**
  - `bicep_curl`
  - `shoulder_press`
  - `lateral_raise`

#### 3. **Reps Selection (OLED)**
```
REPS_SELECTED|10
```
- **When:** User selects rep count on OLED
- **Format:** `REPS_SELECTED|<number>`
- **Example:** `REPS_SELECTED|10`

#### 4. **Sets Selection (OLED)**
```
SETS_SELECTED|3
```
- **When:** User selects set count on OLED
- **Format:** `SETS_SELECTED|<number>`
- **Example:** `SETS_SELECTED|3`

#### 5. **Workout Confirmation**
```
WORKOUT_START_CONFIRMED
```
- **When:** User confirms workout start (press button)
- **Format:** `WORKOUT_START_CONFIRMED` (no parameters)

#### 6. **Position Status**
```
POSITION|at_start
POSITION|moving_to_start
```
- **When:** MPU6050 detects starting position
- **Format:** `POSITION|<status>`
- **Options:**
  - `at_start` - User is in correct starting position
  - `moving_to_start` - User not in position yet

#### 7. **Workout Status**
```
STATUS|waiting
STATUS|ready
STATUS|active
```
- **When:** Workout state changes
- **Format:** `STATUS|<state>`
- **Options:**
  - `waiting` - Waiting for starting position
  - `ready` - Ready to start (in position)
  - `active` - Workout in progress

#### 8. **Rep Count Update**
```
REP_COUNT|5
```
- **When:** MPU6050 detects a completed rep
- **Format:** `REP_COUNT|<current_reps>`
- **Example:** `REP_COUNT|5` (5 reps completed)

#### 9. **Set Progress**
```
SET_PROGRESS|2
```
- **When:** Moving to next set
- **Format:** `SET_PROGRESS|<current_set>`
- **Example:** `SET_PROGRESS|2` (now on set 2)

#### 10. **Calories Burned**
```
CALORIES|12.5
```
- **When:** Calories calculation update
- **Format:** `CALORIES|<float_value>`
- **Example:** `CALORIES|12.5`

#### 11. **Workout Complete**
```
WORKOUT_COMPLETE|bicep_curl|10|3|5.2|28
```
- **When:** All sets completed
- **Format:** `WORKOUT_COMPLETE|exercise_id|reps|sets|duration_min|valid_reps`
- **Example:** `WORKOUT_COMPLETE|bicep_curl|10|3|5.2|28`
  - Exercise: bicep_curl
  - Target: 10 reps × 3 sets = 30 total
  - Duration: 5.2 minutes
  - Valid reps: 28 (93% accuracy)

---

### **From Python → MCU (Messages you receive)**

#### 1. **RFID Response**
```
USER_OK|John
USER_FAIL
```
- **When:** After sending `UID_REQ`
- **Action:** Display username on OLED or show error

#### 2. **Workout Start Command**
```
WORKOUT_START|bicep_curl|10|3
```
- **When:** User starts workout from web frontend
- **Format:** `WORKOUT_START|exercise_id|reps|sets`
- **Action:** Start tracking workout with MPU6050

#### 3. **Workout Cancel**
```
WORKOUT_CANCEL
```
- **When:** User cancels from web
- **Action:** Stop workout, reset state

#### 4. **Frontend Selections (HYBRID Mode)**

**Exercise:**
```
WEB_EXERCISE|bicep_curl
```
- **When:** User selects exercise on web
- **Action:** Display on OLED

**Reps:**
```
WEB_REPS|10
```
- **When:** User selects reps on web
- **Action:** Display on OLED

**Sets:**
```
WEB_SETS|3
```
- **When:** User selects sets on web
- **Action:** Display on OLED

---

## Example MCU Code

### Setup (Arduino/ESP32)

```cpp
#define BAUD_RATE 115200

String inputBuffer = "";

void setup() {
    Serial.begin(BAUD_RATE);
    delay(1000);

    // Clear buffer
    while (Serial.available()) {
        Serial.read();
    }

    // Send ready signal
    Serial.println("MCU_READY");
}

void loop() {
    // Read messages from Python
    checkSerialMessages();

    // Your workout logic here...
}
```

### Reading Messages from Python

```cpp
void checkSerialMessages() {
    while (Serial.available() > 0) {
        char c = Serial.read();

        if (c == '\n') {
            inputBuffer.trim();
            if (inputBuffer.length() > 0) {
                handleMessage(inputBuffer);
                inputBuffer = "";
            }
        } else {
            inputBuffer += c;
        }
    }
}

void handleMessage(String message) {
    // USER_OK|John
    if (message.startsWith("USER_OK")) {
        String username = message.substring(8); // After "USER_OK|"
        displayWelcome(username);
    }

    // USER_FAIL
    else if (message == "USER_FAIL") {
        displayError("Invalid Card");
    }

    // WORKOUT_START|bicep_curl|10|3
    else if (message.startsWith("WORKOUT_START")) {
        int firstPipe = message.indexOf('|');
        int secondPipe = message.indexOf('|', firstPipe + 1);
        int thirdPipe = message.indexOf('|', secondPipe + 1);

        String exercise = message.substring(firstPipe + 1, secondPipe);
        int reps = message.substring(secondPipe + 1, thirdPipe).toInt();
        int sets = message.substring(thirdPipe + 1).toInt();

        startWorkout(exercise, reps, sets);
    }

    // WEB_EXERCISE|bicep_curl
    else if (message.startsWith("WEB_EXERCISE")) {
        String exercise = message.substring(13);
        displayExercise(exercise);
    }

    // WEB_REPS|10
    else if (message.startsWith("WEB_REPS")) {
        int reps = message.substring(9).toInt();
        displayReps(reps);
    }

    // WEB_SETS|3
    else if (message.startsWith("WEB_SETS")) {
        int sets = message.substring(9).toInt();
        displaySets(sets);
    }
}
```

### Sending Messages to Python

```cpp
void sendToFrontend(String message) {
    Serial.println(message);
    Serial.flush(); // Make sure it's sent
    delay(50);      // Small delay for stability
}

// Example usage:
void scanRFID() {
    String uid = readRFIDCard(); // Your RFID reading code
    sendToFrontend("UID_REQ|" + uid);
}

void repDetected() {
    currentReps++;
    sendToFrontend("REP_COUNT|" + String(currentReps));
}

void selectExercise(String exercise_id) {
    sendToFrontend("EXERCISE_SELECTED|" + exercise_id);
}

void confirmWorkout() {
    sendToFrontend("WORKOUT_START_CONFIRMED");
}

void workoutComplete() {
    String msg = "WORKOUT_COMPLETE|";
    msg += exerciseId + "|";
    msg += String(targetReps) + "|";
    msg += String(targetSets) + "|";
    msg += String(durationMin, 1) + "|";
    msg += String(validReps);
    sendToFrontend(msg);
}
```

---

## Message Flow Examples

### **Flow 1: RFID Login**
```
MCU → Python: UID_REQ|7D133721
Python → MCU: USER_OK|John
MCU: Display "Welcome John" on OLED
```

### **Flow 2: OLED Workout Setup**
```
MCU → Python: EXERCISE_SELECTED|bicep_curl
MCU → Python: REPS_SELECTED|10
MCU → Python: SETS_SELECTED|3
MCU → Python: WORKOUT_START_CONFIRMED
MCU → Python: POSITION|at_start
MCU → Python: STATUS|active
MCU → Python: REP_COUNT|1
MCU → Python: REP_COUNT|2
...
MCU → Python: WORKOUT_COMPLETE|bicep_curl|10|3|5.2|30
```

### **Flow 3: Web Frontend Setup**
```
Python → MCU: WEB_EXERCISE|shoulder_press
MCU: Display on OLED
Python → MCU: WEB_REPS|12
MCU: Display on OLED
Python → MCU: WEB_SETS|4
MCU: Display on OLED
Python → MCU: WORKOUT_START|shoulder_press|12|4
MCU: Start workout
```

### **Flow 4: HYBRID Mode**
```
MCU → Python: EXERCISE_SELECTED|bicep_curl (OLED)
Python → MCU: WEB_REPS|10 (Web)
MCU: Display 10 reps on OLED
MCU → Python: SETS_SELECTED|3 (OLED)
MCU → Python: WORKOUT_START_CONFIRMED
```

---

## Important Notes

### ⚠️ Timing & Delays

```cpp
// DON'T send too fast!
sendToFrontend("REP_COUNT|1");
sendToFrontend("REP_COUNT|2");  // Too fast!

// DO add delays:
sendToFrontend("REP_COUNT|1");
delay(200);  // Wait 200ms between messages
sendToFrontend("REP_COUNT|2");
```

### ⚠️ Message Format

```cpp
// ✗ WRONG - No newline
Serial.print("REP_COUNT|5");

// ✓ CORRECT - With newline
Serial.println("REP_COUNT|5");

// ✓ ALSO CORRECT
Serial.print("REP_COUNT|5\n");
```

### ⚠️ Buffer Overflow

```cpp
// Clear serial buffer on startup
void setup() {
    Serial.begin(BAUD_RATE);
    delay(1000);

    // Clear any junk
    while (Serial.available()) {
        Serial.read();
    }
}
```

### ⚠️ Debug Messages

**DON'T send debug messages to Serial:**
```cpp
// ✗ WRONG - Python will see this
Serial.println("Debug: Reading sensor...");

// ✓ CORRECT - Only send protocol messages
if (debugMode) {
    // Use separate debug pin or comment out
}
```

---

## Testing Your MCU

### **Test 1: Echo Test**
```cpp
void loop() {
    if (Serial.available()) {
        String msg = Serial.readStringUntil('\n');
        Serial.println("ECHO: " + msg);
    }
}
```
Run Python, should see echoes in terminal.

### **Test 2: Send UID**
```cpp
void loop() {
    static unsigned long lastSend = 0;
    if (millis() - lastSend > 5000) {
        Serial.println("UID_REQ|7D133721");
        lastSend = millis();
    }
}
```
Run Python, should see login message every 5 seconds.

### **Test 3: Full Workout**
Use the provided `GUI_TEST_SKETCH.ino` for complete testing without hardware.

---

## Troubleshooting

### **Problem: Python doesn't receive messages**
- Check baud rate matches (115200)
- Add `Serial.flush()` after `println`
- Add small delay (50ms) after sending
- Ensure newline (`\n`) at end

### **Problem: Python receives garbage**
- Baud rate mismatch
- Electrical noise on TX/RX lines
- Missing ground connection
- Add delay in setup after `Serial.begin()`

### **Problem: Internal server error**
- **Now fixed!** Error handling added to database queries
- CSV file might have corrupt data
- Check `user_data/` folder for CSV files

### **Problem: Messages appear twice**
- Check you're not printing AND sending
- Disable Arduino Serial Monitor when Python is connected
- Only one program can own the serial port

---

## Quick Reference

| Message | Direction | Format | Example |
|---------|-----------|--------|---------|
| RFID Scan | MCU→PY | `UID_REQ\|uid` | `UID_REQ\|7D133721` |
| Login OK | PY→MCU | `USER_OK\|name` | `USER_OK\|John` |
| Login Fail | PY→MCU | `USER_FAIL` | `USER_FAIL` |
| Exercise (OLED) | MCU→PY | `EXERCISE_SELECTED\|id` | `EXERCISE_SELECTED\|bicep_curl` |
| Reps (OLED) | MCU→PY | `REPS_SELECTED\|num` | `REPS_SELECTED\|10` |
| Sets (OLED) | MCU→PY | `SETS_SELECTED\|num` | `SETS_SELECTED\|3` |
| Confirm | MCU→PY | `WORKOUT_START_CONFIRMED` | `WORKOUT_START_CONFIRMED` |
| Exercise (Web) | PY→MCU | `WEB_EXERCISE\|id` | `WEB_EXERCISE\|bicep_curl` |
| Reps (Web) | PY→MCU | `WEB_REPS\|num` | `WEB_REPS\|10` |
| Sets (Web) | PY→MCU | `WEB_SETS\|num` | `WEB_SETS\|3` |
| Start Workout | PY→MCU | `WORKOUT_START\|id\|r\|s` | `WORKOUT_START\|bicep_curl\|10\|3` |
| Cancel | PY→MCU | `WORKOUT_CANCEL` | `WORKOUT_CANCEL` |
| Position | MCU→PY | `POSITION\|status` | `POSITION\|at_start` |
| Status | MCU→PY | `STATUS\|state` | `STATUS\|active` |
| Rep Count | MCU→PY | `REP_COUNT\|num` | `REP_COUNT|5` |
| Set Progress | MCU→PY | `SET_PROGRESS\|num` | `SET_PROGRESS\|2` |
| Complete | MCU→PY | `WORKOUT_COMPLETE\|...\|valid` | See format above |

---

**Ready to implement!** Use `GUI_TEST_SKETCH.ino` for testing before connecting real hardware.
