/*
 * SmartDumbbell MCU Example Code
 * For Arduino Uno/Nano/ESP32
 *
 * This shows how to properly receive messages from the frontend
 * with proper delays to prevent UART buffer overflow
 */

// Serial Configuration
#define BAUD_RATE 115200
#define SERIAL_BUFFER_SIZE 128

// Workout State
String currentExercise = "";
int targetReps = 0;
int targetSets = 0;
int currentSet = 1;
int currentReps = 0;
bool workoutActive = false;

// Timing
unsigned long lastSerialRead = 0;
unsigned long lastSerialSend = 0;
const unsigned long SERIAL_READ_INTERVAL = 50;   // Read every 50ms
const unsigned long SERIAL_SEND_INTERVAL = 200;  // Send every 200ms minimum

// Message buffer
String inputBuffer = "";

void setup() {
    // Initialize Serial with generous timeout
    Serial.begin(BAUD_RATE);

    // Wait for serial to stabilize
    delay(1000);

    // Clear any garbage in buffer
    while (Serial.available()) {
        Serial.read();
    }

    Serial.println("MCU_READY");
    delay(500);  // Give frontend time to process
}

void loop() {
    // Check for incoming messages (with timing control)
    if (millis() - lastSerialRead >= SERIAL_READ_INTERVAL) {
        checkSerialMessages();
        lastSerialRead = millis();
    }

    // Your main workout logic here
    if (workoutActive) {
        // Monitor MPU, count reps, etc.
        // Call sendToFrontend() when you have updates
    }

    delay(10);  // Small delay to prevent busy loop
}

// ==========================================
// RECEIVE MESSAGES FROM FRONTEND
// ==========================================
void checkSerialMessages() {
    while (Serial.available() > 0) {
        char c = Serial.read();

        if (c == '\n') {
            // Complete message received
            inputBuffer.trim();

            if (inputBuffer.length() > 0) {
                handleMessage(inputBuffer);
                inputBuffer = "";
            }
        } else {
            inputBuffer += c;

            // Prevent buffer overflow
            if (inputBuffer.length() > SERIAL_BUFFER_SIZE) {
                inputBuffer = "";
            }
        }

        // Small delay between character reads
        delay(1);
    }
}

void handleMessage(String message) {
    // Add delay before processing (give time for complete message)
    delay(10);

    // ==========================================
    // USER AUTHENTICATION RESPONSE
    // ==========================================
    if (message.startsWith("USER_OK")) {
        // Format: USER_OK|John
        String username = parseField(message, 1);

        // Display welcome message
        Serial.print("User logged in: ");
        Serial.println(username);

        // Reset workout state
        workoutActive = false;
        currentReps = 0;
        currentSet = 1;
    }

    else if (message.equals("USER_FAIL")) {
        // RFID authentication failed
        Serial.println("Authentication failed");
        // Show error on display, beep, etc.
    }

    // ==========================================
    // WORKOUT START
    // ==========================================
    else if (message.startsWith("WORKOUT_START")) {
        // Format: WORKOUT_START|bicep_curl|10|3

        currentExercise = parseField(message, 1);  // "bicep_curl"
        targetReps = parseField(message, 2).toInt();  // 10
        targetSets = parseField(message, 3).toInt();  // 3

        // Reset counters
        currentSet = 1;
        currentReps = 0;
        workoutActive = true;

        // Display workout info
        Serial.println("=== WORKOUT STARTED ===");
        Serial.print("Exercise: ");
        Serial.println(currentExercise);
        Serial.print("Target: ");
        Serial.print(targetReps);
        Serial.print(" reps × ");
        Serial.print(targetSets);
        Serial.println(" sets");

        // Send initial status
        delay(50);
        sendToFrontend("STATUS|waiting");

        // Start monitoring for starting position
        checkStartingPosition();
    }

    // ==========================================
    // WORKOUT CANCEL
    // ==========================================
    else if (message.equals("WORKOUT_CANCEL")) {
        workoutActive = false;
        currentReps = 0;
        currentSet = 1;
        Serial.println("Workout cancelled");
    }
}

// ==========================================
// SEND MESSAGES TO FRONTEND
// ==========================================
void sendToFrontend(String message) {
    // Enforce minimum time between sends
    unsigned long timeSinceLastSend = millis() - lastSerialSend;
    if (timeSinceLastSend < SERIAL_SEND_INTERVAL) {
        delay(SERIAL_SEND_INTERVAL - timeSinceLastSend);
    }

    // Send with newline
    Serial.println(message);

    // CRITICAL: Wait for data to actually transmit
    Serial.flush();

    // Add delay after sending
    delay(50);

    lastSerialSend = millis();
}

// ==========================================
// STARTING POSITION DETECTION (EXAMPLE)
// ==========================================
void checkStartingPosition() {
    // TODO: Read MPU6050 angles
    // float pitch = getMPUPitch();
    // float roll = getMPURoll();

    // Example for bicep curl: arm at ~90 degrees
    bool atStartingPosition = false; // Replace with actual MPU check

    if (atStartingPosition) {
        sendToFrontend("POSITION|at_start");
        sendToFrontend("STATUS|ready");

        // Start workout monitoring
        startRepCounting();
    } else {
        sendToFrontend("POSITION|moving_to_start");
        sendToFrontend("STATUS|waiting");
    }
}

// ==========================================
// REP COUNTING (EXAMPLE)
// ==========================================
void startRepCounting() {
    sendToFrontend("STATUS|active");

    // Main rep counting loop
    while (currentSet <= targetSets && workoutActive) {
        // Check for incoming messages (e.g., cancel)
        checkSerialMessages();

        // TODO: Detect rep from MPU
        bool repDetected = detectRep();  // Your MPU logic here

        if (repDetected) {
            currentReps++;

            // Send rep count update
            sendToFrontend("REP_COUNT|" + String(currentReps));

            // Check if set complete
            if (currentReps >= targetReps) {
                currentSet++;
                currentReps = 0;

                if (currentSet <= targetSets) {
                    // Send set progress
                    sendToFrontend("SET_PROGRESS|" + String(currentSet));

                    // Rest period between sets (optional)
                    delay(2000);
                }
            }
        }

        delay(50);  // Small delay in loop
    }

    // Workout complete
    if (currentSet > targetSets) {
        sendWorkoutComplete();
    }
}

void sendWorkoutComplete() {
    // Format: WORKOUT_COMPLETE|exercise|reps|sets|duration|valid_reps

    float durationMinutes = 5.2;  // TODO: Calculate from timer
    int validReps = 28;           // TODO: Track during workout

    String message = "WORKOUT_COMPLETE|";
    message += currentExercise + "|";
    message += String(targetReps) + "|";
    message += String(targetSets) + "|";
    message += String(durationMinutes, 1) + "|";
    message += String(validReps);

    sendToFrontend(message);

    workoutActive = false;
}

// ==========================================
// HELPER FUNCTIONS
// ==========================================

// Parse field from pipe-separated message
String parseField(String message, int fieldIndex) {
    int currentField = 0;
    int startPos = 0;

    for (int i = 0; i <= message.length(); i++) {
        if (i == message.length() || message.charAt(i) == '|') {
            if (currentField == fieldIndex) {
                return message.substring(startPos, i);
            }
            currentField++;
            startPos = i + 1;
        }
    }

    return "";
}

// Placeholder for rep detection
bool detectRep() {
    // TODO: Implement MPU-based rep detection
    // Read accelerometer/gyroscope
    // Analyze movement pattern
    // Return true when valid rep detected
    return false;
}

// ==========================================
// RFID SCANNING (EXAMPLE)
// ==========================================
void scanRFID() {
    // TODO: Read RFID card
    // When card detected, send to frontend:

    String cardUID = "7D133721";  // Example

    // Send RFID request
    sendToFrontend("UID_REQ|" + cardUID);

    // Wait for response (USER_OK or USER_FAIL)
    // Response will come via handleMessage()
}
