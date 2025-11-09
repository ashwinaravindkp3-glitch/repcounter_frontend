/*
 * ================================================
 * SmartDumbbell GUI Test & Debug Sketch
 * ================================================
 *
 * This sketch simulates the complete MCU behavior for testing
 * the frontend GUI without needing actual hardware (RFID, MPU6050)
 *
 * Upload to: Arduino Uno/Nano/Mega or ESP32
 * Baud Rate: 115200
 *
 * FEATURES:
 * - Simulates RFID card scans
 * - Simulates complete workout flow
 * - Multiple test scenarios
 * - Realistic timing and rep counting
 * - Interactive menu for testing
 *
 * USAGE:
 * 1. Upload to Arduino
 * 2. Run Python frontend (python main.py)
 * 3. Open Serial Monitor (115200 baud)
 * 4. Send commands to trigger test scenarios
 *
 * ================================================
 */

#define BAUD_RATE 115200

// Test Configuration
bool autoMode = false;           // Auto-run test scenarios
bool debugMode = true;           // Print debug messages
unsigned long lastSerialSend = 0;
const unsigned long SEND_INTERVAL = 200;  // 200ms between sends

// Workout State
String currentExercise = "";
int targetReps = 0;
int targetSets = 0;
int currentSet = 1;
int currentReps = 0;
bool workoutActive = false;
unsigned long workoutStartTime = 0;

// Test Users (RFID UIDs)
String testUsers[] = {
    "7D133721",  // John (default in frontend)
    "00000000",  // Sarah
    "12345678"   // Unknown user (will fail)
};

// Message buffer
String inputBuffer = "";

// ================================================
// SETUP
// ================================================
void setup() {
    Serial.begin(BAUD_RATE);
    delay(1000);

    // Clear buffer
    while (Serial.available()) {
        Serial.read();
    }

    sendToFrontend("MCU_READY");

    Serial.println();
    Serial.println(F("╔════════════════════════════════════════════╗"));
    Serial.println(F("║   SmartDumbbell GUI Test & Debug Sketch   ║"));
    Serial.println(F("╚════════════════════════════════════════════╝"));
    Serial.println();
    printMenu();
}

// ================================================
// MAIN LOOP
// ================================================
void loop() {
    // Check for incoming messages from frontend
    checkSerialMessages();

    // Check for test commands from Serial Monitor
    checkTestCommands();

    // Auto-test mode
    if (autoMode && !workoutActive) {
        delay(3000);  // Wait between auto tests
        runAutoTest();
    }

    delay(10);
}

// ================================================
// MENU
// ================================================
void printMenu() {
    Serial.println(F("═══════════════ TEST COMMANDS ═══════════════"));
    Serial.println(F("RFID Tests:"));
    Serial.println(F("  1 - Scan valid RFID (John)"));
    Serial.println(F("  2 - Scan valid RFID (Sarah)"));
    Serial.println(F("  3 - Scan invalid RFID"));
    Serial.println();
    Serial.println(F("Workout Tests:"));
    Serial.println(F("  4 - Quick workout (5 reps, 2 sets, fast)"));
    Serial.println(F("  5 - Medium workout (10 reps, 3 sets)"));
    Serial.println(F("  6 - Long workout (15 reps, 5 sets)"));
    Serial.println(F("  7 - Perfect form workout (100% accuracy)"));
    Serial.println(F("  8 - Poor form workout (60% accuracy)"));
    Serial.println();
    Serial.println(F("Position Tests:"));
    Serial.println(F("  9 - Test starting position detection"));
    Serial.println();
    Serial.println(F("Special:"));
    Serial.println(F("  a - Auto-run all tests"));
    Serial.println(F("  m - Show this menu"));
    Serial.println(F("  d - Toggle debug mode"));
    Serial.println(F("═════════════════════════════════════════════"));
    Serial.println();
}

// ================================================
// RECEIVE FROM FRONTEND
// ================================================
void checkSerialMessages() {
    while (Serial.available() > 0) {
        char c = Serial.read();

        if (c == '\n') {
            inputBuffer.trim();
            if (inputBuffer.length() > 0) {
                handleFrontendMessage(inputBuffer);
                inputBuffer = "";
            }
        } else {
            inputBuffer += c;
            if (inputBuffer.length() > 128) {
                inputBuffer = "";  // Prevent overflow
            }
        }
        delay(1);
    }
}

void handleFrontendMessage(String message) {
    if (debugMode) {
        Serial.print(F("← Frontend: "));
        Serial.println(message);
    }

    // User authentication response
    if (message.startsWith("USER_OK")) {
        String username = parseField(message, 1);
        Serial.print(F("✓ Login successful: "));
        Serial.println(username);
        Serial.println(F("→ Go to dashboard and select an exercise!"));
    }
    else if (message.equals("USER_FAIL")) {
        Serial.println(F("✗ Login failed - Invalid RFID card"));
    }

    // Workout start
    else if (message.startsWith("WORKOUT_START")) {
        currentExercise = parseField(message, 1);
        targetReps = parseField(message, 2).toInt();
        targetSets = parseField(message, 3).toInt();

        Serial.println();
        Serial.println(F("╔════════════════════════════════════════╗"));
        Serial.println(F("║       WORKOUT STARTED FROM GUI         ║"));
        Serial.println(F("╚════════════════════════════════════════╝"));
        Serial.print(F("Exercise: "));
        Serial.println(currentExercise);
        Serial.print(F("Target: "));
        Serial.print(targetReps);
        Serial.print(F(" reps × "));
        Serial.print(targetSets);
        Serial.println(F(" sets"));
        Serial.println();

        // Start simulated workout
        startSimulatedWorkout();
    }

    // Workout cancel
    else if (message.equals("WORKOUT_CANCEL")) {
        Serial.println(F("✗ Workout cancelled from GUI"));
        workoutActive = false;
    }
}

// ================================================
// TEST COMMANDS FROM SERIAL MONITOR
// ================================================
void checkTestCommands() {
    if (Serial.available() > 0) {
        char cmd = Serial.read();

        // Clear rest of input
        while (Serial.available()) {
            Serial.read();
        }

        switch (cmd) {
            case '1':
                Serial.println(F("\n[TEST] Valid RFID scan - John"));
                simulateRFIDScan(testUsers[0]);
                break;

            case '2':
                Serial.println(F("\n[TEST] Valid RFID scan - Sarah"));
                simulateRFIDScan(testUsers[1]);
                break;

            case '3':
                Serial.println(F("\n[TEST] Invalid RFID scan"));
                simulateRFIDScan(testUsers[2]);
                break;

            case '4':
                Serial.println(F("\n[TEST] Quick workout"));
                targetReps = 5;
                targetSets = 2;
                currentExercise = "bicep_curl";
                Serial.println(F("→ Select workout from GUI with 5 reps, 2 sets"));
                break;

            case '5':
                Serial.println(F("\n[TEST] Medium workout"));
                targetReps = 10;
                targetSets = 3;
                currentExercise = "shoulder_press";
                Serial.println(F("→ Select workout from GUI with 10 reps, 3 sets"));
                break;

            case '6':
                Serial.println(F("\n[TEST] Long workout"));
                targetReps = 15;
                targetSets = 5;
                currentExercise = "lateral_raise";
                Serial.println(F("→ Select workout from GUI with 15 reps, 5 sets"));
                break;

            case '7':
                Serial.println(F("\n[TEST] Perfect form workout"));
                Serial.println(F("→ Select workout from GUI, will show 100% accuracy"));
                break;

            case '8':
                Serial.println(F("\n[TEST] Poor form workout"));
                Serial.println(F("→ Select workout from GUI, will show ~60% accuracy"));
                break;

            case '9':
                Serial.println(F("\n[TEST] Starting position detection"));
                testStartingPosition();
                break;

            case 'a':
            case 'A':
                Serial.println(F("\n[TEST] Auto-run mode started"));
                autoMode = true;
                break;

            case 'm':
            case 'M':
                printMenu();
                break;

            case 'd':
            case 'D':
                debugMode = !debugMode;
                Serial.print(F("Debug mode: "));
                Serial.println(debugMode ? F("ON") : F("OFF"));
                break;

            default:
                if (cmd != '\n' && cmd != '\r') {
                    Serial.println(F("Unknown command. Press 'm' for menu."));
                }
                break;
        }
    }
}

// ================================================
// SIMULATE RFID SCAN
// ================================================
void simulateRFIDScan(String uid) {
    Serial.print(F("→ Scanning RFID card: "));
    Serial.println(uid);

    sendToFrontend("UID_REQ|" + uid);

    Serial.println(F("→ Waiting for authentication..."));
}

// ================================================
// SIMULATE STARTING POSITION DETECTION
// ================================================
void testStartingPosition() {
    Serial.println(F("Simulating starting position detection..."));

    // Not at position
    Serial.println(F("  [1/3] User moving to position..."));
    sendToFrontend("POSITION|moving_to_start");
    sendToFrontend("STATUS|waiting");
    delay(1500);

    // Still not at position
    Serial.println(F("  [2/3] Still moving..."));
    sendToFrontend("POSITION|moving_to_start");
    delay(1500);

    // Reached position
    Serial.println(F("  [3/3] Position reached!"));
    sendToFrontend("POSITION|at_start");
    sendToFrontend("STATUS|ready");

    Serial.println(F("✓ Starting position test complete"));
}

// ================================================
// SIMULATE WORKOUT
// ================================================
void startSimulatedWorkout() {
    workoutActive = true;
    currentSet = 1;
    currentReps = 0;
    workoutStartTime = millis();

    // Step 1: Wait for starting position
    Serial.println(F("\n[Step 1] Waiting for starting position..."));
    delay(500);
    sendToFrontend("STATUS|waiting");
    sendToFrontend("POSITION|moving_to_start");
    delay(2000);

    // Step 2: Reached starting position
    Serial.println(F("[Step 2] Starting position reached!"));
    sendToFrontend("POSITION|at_start");
    sendToFrontend("STATUS|ready");
    delay(1500);

    // Step 3: Start workout
    Serial.println(F("[Step 3] Starting workout..."));
    sendToFrontend("STATUS|active");
    delay(1000);

    // Step 4: Simulate sets and reps
    for (currentSet = 1; currentSet <= targetSets && workoutActive; currentSet++) {
        Serial.println();
        Serial.print(F("═══ SET "));
        Serial.print(currentSet);
        Serial.print(F(" / "));
        Serial.print(targetSets);
        Serial.println(F(" ═══"));

        // Simulate reps in this set
        for (currentReps = 1; currentReps <= targetReps && workoutActive; currentReps++) {
            // Check for cancel
            checkSerialMessages();
            if (!workoutActive) break;

            // Simulate rep (realistic timing: 2-3 seconds per rep)
            delay(random(2000, 3500));

            // Send rep count
            sendToFrontend("REP_COUNT|" + String(currentReps));

            // Calculate and send calories
            float caloriesPerRep = getCaloriesPerRep(currentExercise);
            int totalReps = (currentSet - 1) * targetReps + currentReps;
            float totalCalories = totalReps * caloriesPerRep;
            sendToFrontend("CALORIES|" + String(totalCalories, 1));

            Serial.print(F("  Rep "));
            Serial.print(currentReps);
            Serial.print(F("/"));
            Serial.print(targetReps);
            Serial.print(F(" | Calories: "));
            Serial.println(totalCalories, 1);
        }

        // Set complete
        if (currentSet < targetSets && workoutActive) {
            Serial.println(F("  ✓ Set complete!"));
            delay(500);
            sendToFrontend("SET_PROGRESS|" + String(currentSet + 1));

            // Rest period between sets
            Serial.println(F("  → Rest period (3 seconds)..."));
            delay(3000);
        }
    }

    // Step 5: Workout complete
    if (workoutActive) {
        Serial.println();
        Serial.println(F("╔════════════════════════════════════════╗"));
        Serial.println(F("║        WORKOUT COMPLETE! 🎉            ║"));
        Serial.println(F("╚════════════════════════════════════════╝"));

        // Calculate workout stats
        float durationMinutes = (millis() - workoutStartTime) / 60000.0;
        int totalReps = targetReps * targetSets;
        int validReps = random(totalReps * 0.8, totalReps + 1);  // 80-100% valid

        Serial.print(F("Duration: "));
        Serial.print(durationMinutes, 1);
        Serial.println(F(" minutes"));
        Serial.print(F("Total reps: "));
        Serial.println(totalReps);
        Serial.print(F("Valid reps: "));
        Serial.print(validReps);
        Serial.print(F(" ("));
        Serial.print(validReps * 100 / totalReps);
        Serial.println(F("%)"));

        // Send completion message
        String completeMsg = "WORKOUT_COMPLETE|";
        completeMsg += currentExercise + "|";
        completeMsg += String(targetReps) + "|";
        completeMsg += String(targetSets) + "|";
        completeMsg += String(durationMinutes, 1) + "|";
        completeMsg += String(validReps);

        sendToFrontend(completeMsg);

        Serial.println();
        Serial.println(F("→ Check GUI for workout summary!"));
        Serial.println();
    }

    workoutActive = false;
}

// ================================================
// AUTO TEST MODE
// ================================================
void runAutoTest() {
    static int testIndex = 0;

    Serial.println();
    Serial.print(F("╔═══ AUTO TEST #"));
    Serial.print(testIndex + 1);
    Serial.println(F(" ═══╗"));

    switch (testIndex) {
        case 0:
            Serial.println(F("→ Testing RFID login..."));
            simulateRFIDScan(testUsers[0]);
            break;

        case 1:
            Serial.println(F("→ Testing position detection..."));
            testStartingPosition();
            break;

        case 2:
            Serial.println(F("→ User should select exercise from GUI now..."));
            Serial.println(F("→ Waiting for WORKOUT_START message..."));
            break;

        default:
            Serial.println(F("✓ Auto tests complete!"));
            autoMode = false;
            testIndex = -1;
            break;
    }

    testIndex++;
}

// ================================================
// HELPER FUNCTIONS
// ================================================

void sendToFrontend(String message) {
    // Enforce minimum delay between sends
    unsigned long timeSinceLastSend = millis() - lastSerialSend;
    if (timeSinceLastSend < SEND_INTERVAL) {
        delay(SEND_INTERVAL - timeSinceLastSend);
    }

    if (debugMode) {
        Serial.print(F("→ Frontend: "));
        Serial.println(message);
    }

    Serial.println(message);
    Serial.flush();  // CRITICAL!
    delay(50);

    lastSerialSend = millis();
}

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

float getCaloriesPerRep(String exercise) {
    if (exercise == "bicep_curl") return 0.5;
    if (exercise == "shoulder_press") return 0.7;
    if (exercise == "lateral_raise") return 0.6;
    return 0.5;  // Default
}

// ================================================
// END OF TEST SKETCH
// ================================================
