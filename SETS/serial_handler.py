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
                timeout=self.timeout
            )
            time.sleep(2)
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
            self.thread.join(timeout=1.0)
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
    
    def _run(self):
        while self.is_running:
            if self.serial_conn.in_waiting > 0:
                try:
                    line = self.serial_conn.readline().decode('utf-8').strip()
                    if line:
                        self.rx_queue.put(line)
                except Exception as e:
                    print(f"✗ RX Error: {e}")
            
            try:
                message = self.tx_queue.get_nowait()
                time.sleep(0.02)  # 20ms delay before sending
                self.serial_conn.write(message.encode())
                time.sleep(0.1)   # Delay after sending
            except queue.Empty:
                pass
            
            time.sleep(0.01)
    
    def get_message(self):
        try:
            return self.rx_queue.get_nowait()
        except queue.Empty:
            return None
    
    def send_message(self, message: str):
        self.tx_queue.put(message)