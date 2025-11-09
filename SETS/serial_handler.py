# serial_handler.py
import serial
import threading
import queue
import time

class SerialHandler:
    def __init__(self, port: str, baudrate: int, timeout: float):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn = None

        self.rx_queue = queue.Queue()
        self.tx_queue = queue.Queue()
        self.is_running = False
        self.thread = None

    def start(self) -> bool:
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=2.0  # 2 second write timeout
            )
            # Give MCU time to reset after serial connection
            print("⏳ Waiting for MCU to initialize (3 seconds)...")
            time.sleep(3)

            # Clear any garbage data in buffer
            self.serial_conn.reset_input_buffer()
            self.serial_conn.reset_output_buffer()

            self.is_running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            return True
        except serial.SerialException as e:
            print(f"✗ Serial connection failed: {e}")
            return False

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()

    def _run(self):
        """Background thread for serial communication with MCU-friendly delays"""
        last_tx_time = 0

        while self.is_running:
            # ==========================================
            # RECEIVE FROM MCU
            # ==========================================
            if self.serial_conn.in_waiting > 0:
                try:
                    line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        self.rx_queue.put(line)
                        print(f"← RX: {line}")  # Debug: show received
                except Exception as e:
                    print(f"✗ RX Error: {e}")

            # ==========================================
            # SEND TO MCU (with generous delays)
            # ==========================================
            try:
                message = self.tx_queue.get_nowait()

                # Ensure minimum 200ms between messages
                time_since_last_tx = time.time() - last_tx_time
                if time_since_last_tx < 0.2:  # 200ms minimum gap
                    time.sleep(0.2 - time_since_last_tx)

                # Send message with delays
                print(f"→ TX: {message.strip()}")  # Debug: show sending

                # Add generous pre-send delay
                time.sleep(0.05)  # 50ms before sending

                # Send the message
                self.serial_conn.write(message.encode('utf-8'))

                # CRITICAL: Flush to ensure data is sent immediately
                self.serial_conn.flush()

                # Add generous post-send delay for MCU to process
                time.sleep(0.15)  # 150ms after sending

                last_tx_time = time.time()

            except queue.Empty:
                pass
            except Exception as e:
                print(f"✗ TX Error: {e}")

            # Slow loop to avoid CPU hogging
            time.sleep(0.02)  # 20ms loop delay

    def get_message(self):
        """Get received message from MCU (non-blocking)"""
        try:
            return self.rx_queue.get_nowait()
        except queue.Empty:
            return None

    def send_message(self, message: str):
        """
        Queue message to send to MCU
        Message will be sent with proper delays automatically
        """
        # Ensure message ends with newline for MCU parsing
        if not message.endswith('\n'):
            message += '\n'

        self.tx_queue.put(message)

    def send_message_blocking(self, message: str, wait_time: float = 0.3):
        """
        Send message and wait (blocking)
        Use this for critical messages that need guaranteed delivery

        Args:
            message: Message to send
            wait_time: Time to wait after sending (default 300ms)
        """
        if not message.endswith('\n'):
            message += '\n'

        try:
            print(f"→ TX (blocking): {message.strip()}")

            # Pre-send delay
            time.sleep(0.05)

            # Send
            self.serial_conn.write(message.encode('utf-8'))
            self.serial_conn.flush()

            # Post-send delay (generous for MCU processing)
            time.sleep(wait_time)

        except Exception as e:
            print(f"✗ TX Error (blocking): {e}")
