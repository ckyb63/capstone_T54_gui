# === Imports ===
# Standard Library
import sys
import os
import time
import threading
import platform
import traceback
import serial
import serial.tools.list_ports

# Third-Party
import cv2
import torch
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGridLayout, QLineEdit, QMessageBox, QFrame,
    QTextEdit, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, Slot
from PySide6.QtGui import QFont, QImage, QPixmap, QPainter, QPen

# Local Imports
try:
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
    from avend_api_client.avend_api import AvendAPI
except ImportError:
    print("WARNING: avend_api_client not found. Using Mock AvendAPI.")
    class AvendAPI:
        def __init__(self, host="127.0.0.1", port=8080):
            self.base_url = f"http://{host}:{port}/avend"
            print(f"Mock AvendAPI initialized: {self.base_url}")
        def start_session(self): return {"success": True, "response": "Mock session"}
        def dispense(self, code=None): return {"success": True, "response": f"Mock dispense {code}"}
        def start_service_routine(self): return {"success": True, "response": "Mock H1 start"}
        def stop_service_routine(self): return {"success": True, "response": "Mock H1 stop"}

try:
    from capstone_model import run_detection, try_open_camera, get_linux_cameras, print_camera_info
    HAS_DETECTION_MODEL = True
except ImportError as e:
    print(f"WARNING: Failed to import from capstone_model: {e}. Using mock detection.")
    HAS_DETECTION_MODEL = False
    def run_detection(): return {'model': None}
    def try_open_camera(idx, **kwargs): return None
    def get_linux_cameras(): return []
    def print_camera_info(cap, idx): pass

# === Constants ===
DEFAULT_AVEND_IP = "192.168.0.3"
DEFAULT_AVEND_PORT = "8080"
CAMERA_FEED_WIDTH = 400
CAMERA_FEED_HEIGHT = 300
DETECTION_RESOLUTION = (640, 480) # Resolution used during model detection
BUTTON_WIDTH = 150
BUTTON_HEIGHT = 90
MISS_THRESHOLD = 50 # Consecutive misses before button turns red
OVERRIDE_DURATION_MS = 15000 # 15 seconds
STATUS_RESET_DELAY_MS = 3000 # 3 seconds
H1_SERVICE_DELAY_MS = 3000 # 3 seconds
version = "0.11.0"

# === Detection Thread ===
class DetectionThread(QThread):
    """
    Worker thread for handling camera capture and PPE detection inference.

    Emits raw camera frames and detection results (states and boxes)
    via signals to the main GUI thread. Runs predictions in a separate
    sub-thread to avoid blocking the camera feed.
    """
    detection_signal = Signal(dict) # Emits {'states': dict, 'boxes': list}
    camera_status_signal = Signal(object) # Emits None, True, or False
    frame_signal = Signal(QImage) # Emits raw camera frames

    def __init__(self):
        """Initializes thread state variables and lock."""
        super().__init__()
        self.is_running = True
        self.config = None
        self.model = None
        self.cap = None
        self.lock = threading.Lock()
        self.current_camera_index = None # Added to store the working index
        # Initial state assumes nothing detected
        self.latest_states = {
            "hardhat": False, "glasses": False, "vest": False,
            "earplugs": False, "gloves": False
        }
        self.latest_boxes = []
        self.prediction_running = False
        self._initial_camera_status_sent = False

    def _run_prediction(self, frame_copy):
        """
        Performs YOLO prediction in a background thread.

        Updates shared state (latest_states, latest_boxes) upon completion.
        Args:
            frame_copy: A numpy array copy of the frame to predict on.
        """
        # Initialize locals for THIS prediction run
        prediction_states = {key: False for key in self.latest_states}
        prediction_boxes = []
        device_to_use = 'cpu'
        detection_summary = []

        try:
            if self.model is None:
                 print("Prediction skipped: Model not loaded.")
                 with self.lock:
                    self.latest_states = prediction_states
                    self.latest_boxes = prediction_boxes
                 return

            if torch.cuda.is_available():
                device_to_use = 'cuda:0'

            results = self.model.predict(frame_copy, conf=0.5, verbose=False, stream=True, device=device_to_use)

            processed_a_result = False
            for result in results:
                processed_a_result = True
                if result.boxes:
                    for box in result.boxes:
                        class_index = int(box.cls)
                        confidence = float(box.conf)
                        if self.model.names:
                            class_name = self.model.names[class_index].lower()
                            if class_name in self.config['class_map']:
                                button_key = self.config['class_map'][class_name]
                                prediction_states[button_key] = True
                                try:
                                     coords = box.xyxy[0].cpu().numpy().astype(int)
                                     prediction_boxes.append({'coords': coords.tolist(), 'label': class_name, 'conf': confidence})
                                     detection_summary.append(f"{class_name} ({confidence:.2f})")
                                except Exception as e:
                                     print(f"Error processing box data: {e}")
                break

            if detection_summary:
                 print(f"[Detection] Found: {', '.join(detection_summary)}")

            # Update shared state with results from this run
            with self.lock:
                self.latest_states = prediction_states
                self.latest_boxes = prediction_boxes

        except Exception as e:
            print(f"Error during prediction sub-thread: {e}")
            traceback.print_exc()
            print("Clearing detection state due to prediction error.")
            with self.lock:
                self.latest_states = {key: False for key in self.latest_states}
                self.latest_boxes = []
        finally:
            with self.lock:
                self.prediction_running = False

    def run(self):
        """Main loop: Reads camera frames, emits them, and dispatches predictions."""
        try:
            self.config = run_detection()
            self.model = self.config.get('model')

            if self.model is None and HAS_DETECTION_MODEL:
                print("DetectionThread: Model loaded but is None. Cannot run detection.")
                self.camera_status_signal.emit(None)
                self._initial_camera_status_sent = True
                return
            elif not HAS_DETECTION_MODEL:
                 print("DetectionThread: Real model not available. Thread will not run detection logic.")
                 self.camera_status_signal.emit(None)
                 self._initial_camera_status_sent = True
                 # In a real scenario without a model, maybe loop sending mock data or exit?
                 # For now, just exit if the real model components are missing.
                 return

            print("\nInitializing camera detection system in DetectionThread...")
            self.camera_status_signal.emit(None)
            self._initial_camera_status_sent = True

            # Open Camera
            self.cap = None
            self.current_camera_index = None # Reset index before trying
            if platform.system() != "Windows":
                preferred_indices = [1, 2, 0]
                for index in preferred_indices:
                    print(f"\n--- Trying camera index {index} (Linux) ---")
                    self.cap = try_open_camera(index, max_retries=2, retry_delay=1.5)
                    if self.cap:
                        self.current_camera_index = index # Store successful index
                        print(f"*** Camera successfully opened on index {self.current_camera_index} ***")
                        break
            else:
                print("\n--- Trying external camera (index 1 - Windows) ---")
                self.cap = try_open_camera(1, max_retries=3, retry_delay=1.5)
                if self.cap:
                    self.current_camera_index = 1 # Store successful index
                    print(f"*** Camera successfully opened on index {self.current_camera_index} ***")
                else:
                    print("\n--- External camera failed, trying built-in camera (index 0 - Windows) ---")
                    self.cap = try_open_camera(0, max_retries=2, retry_delay=1.0)
                    if self.cap:
                        self.current_camera_index = 0 # Store successful index
                        print(f"*** Camera successfully opened on index {self.current_camera_index} ***")

            if not self.cap or not self.cap.isOpened():
                print("FATAL: Failed to initialize ANY camera in DetectionThread.")
                self.camera_status_signal.emit(False)
                return
            # If we got here, self.current_camera_index should hold the working index

            print(f"\nCamera setup complete using index {self.current_camera_index}. Starting detection loop...")
            self.camera_status_signal.emit(True)

            frame_count = 0
            fps_start_time = time.time()
            read_fps_start_time = time.time()
            fps_frame_count = 0
            read_frame_count = 0
            target_frame_time = 1.0 / self.config.get('display_fps', 30)
            detection_interval = self.config.get('detection_interval', 10)

            while self.is_running:
                loop_start_time = time.time()
                ret, frame = self.cap.read()
                read_time = time.time() - loop_start_time

                if not ret:
                    print(f"Error reading frame (read took {read_time:.4f}s). Retrying...")
                    time.sleep(0.5)
                    continue

                read_frame_count += 1
                frame_count += 1
                fps_frame_count += 1

                # Emit Raw Frame
                if frame is not None:
                    try:
                        display_frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        h, w, ch = display_frame_rgb.shape
                        bytes_per_line = ch * w
                        qt_image = QImage(display_frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                        self.frame_signal.emit(qt_image)
                    except Exception as e:
                         print(f"Error converting/emitting frame: {e}")

                # Emit Current State Payload
                try:
                    with self.lock:
                        payload = {
                            'states': self.latest_states.copy(),
                            'boxes': self.latest_boxes
                        }
                    self.detection_signal.emit(payload)
                except Exception as e:
                    print(f"Error emitting detection payload: {e}")

                # Dispatch Prediction Thread
                with self.lock:
                    pred_running = self.prediction_running

                if frame_count % detection_interval == 0 and not pred_running:
                    try:
                        with self.lock:
                             self.prediction_running = True
                        predict_thread = threading.Thread(target=self._run_prediction, args=(frame.copy(),), daemon=True)
                        predict_thread.start()
                    except Exception as e:
                        print(f"Error starting prediction thread: {e}")
                        with self.lock:
                             self.prediction_running = False

                # FPS Logging
                current_time = time.time()
                if current_time - fps_start_time >= 5.0:
                    loop_fps = fps_frame_count / (current_time - fps_start_time)
                    actual_read_fps = read_frame_count / (current_time - read_fps_start_time)
                    with self.lock: pred_running_status = self.prediction_running
                    print(f"Stats (5s avg): Loop FPS: {loop_fps:.2f}, Read FPS: {actual_read_fps:.2f}, Last read: {read_time:.4f}s, Predicting: {pred_running_status}")

                    # --- Check Read FPS and attempt restart if low ---
                    if actual_read_fps < 5.0 and self.current_camera_index is not None:
                        print(f"WARNING: Read FPS ({actual_read_fps:.2f}) below threshold (5 FPS). Attempting camera restart on stored index {self.current_camera_index}...")
                        if self.cap:
                            self.cap.release()
                            self.cap = None
                        time.sleep(1.0) # Give some time before retrying
                        self.cap = try_open_camera(self.current_camera_index, max_retries=2, retry_delay=1.0)
                        if self.cap:
                            print(f"Camera successfully restarted on index {self.current_camera_index}.")
                            self.camera_status_signal.emit(True) # Re-signal connection
                        else:
                            print(f"ERROR: Failed to restart camera on index {self.current_camera_index}. Will retry check later.")
                            self.camera_status_signal.emit(False) # Signal temporary failure

                    # Reset FPS counters and timers
                    fps_frame_count = 0
                    read_frame_count = 0
                    fps_start_time = current_time
                    read_fps_start_time = current_time

                # Loop Rate Control
                loop_duration = time.time() - loop_start_time
                sleep_time = max(0, target_frame_time - loop_duration)
                if sleep_time > 0:
                    time.sleep(sleep_time)

            # --- Cleanup ---
            print("Exiting detection loop. Cleaning up camera resources...")
            if self.cap:
                self.cap.release()
            print("DetectionThread cleanup complete.")
            self.camera_status_signal.emit(False)

        except Exception as e:
            print(f"\n--- CRITICAL ERROR IN DetectionThread RUN METHOD ---")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {str(e)}")
            traceback.print_exc()
            print("--------------------------------------------------")
            status_to_emit = False if self._initial_camera_status_sent else None
            self.camera_status_signal.emit(status_to_emit)
            if self.cap and self.cap.isOpened():
                 self.cap.release()
                 print("Camera released after error.")

    def stop(self):
        """Signals the run loop to stop."""
        print("DetectionThread stop called.")
        self.is_running = False

# === Main Window ===
class MainWindow(QMainWindow):
    """
    Main application window for the PPE Vending Machine GUI.

    Handles UI layout, user interactions, communication with the
    DetectionThread and AVend API.
    """
    def __init__(self):
        """Initializes the main window, UI components, and state."""
        super().__init__()

        # --- Core Attributes ---
        self.api = AvendAPI(host=DEFAULT_AVEND_IP, port=DEFAULT_AVEND_PORT)
        self.avend_codes = {
            "hardhat": "8D1", 
            "glasses": "8C2", 
            "vest": "8A4",
            "earplugs": "8E7",
            "gloves": "8B3"
        }
        self.item_names = {
            "hardhat": "Hard Hat", "glasses": "Safety Glasses", "vest": "Hi-Vis Vest",
            "earplugs": "Ear Plugs", "gloves": "Gloves"
        }
        self.ppe_keys = list(self.item_names.keys())

        # --- UI Colors --- #
        self.primary_color = "#FF7B7B" # Reddish (buttons default)
        self.secondary_color = "#FFA500" # Orange (override, status)
        self.success_color = "#34C759" # Green (detected, success)
        self.danger_color = "#FF3B30" # Red (missing, error)
        self.nav_color = "#007AFF" # Blue (nav buttons)
        self.nav_hover_color = "#0062CC"
        self.nav_pressed_color = "#004999"
        self.nav_active_color = self.success_color # Green when nav active

        # --- State Tracking --- #
        self.latest_received_boxes = []
        self.detection_resolution = DETECTION_RESOLUTION
        self.ppe_missing_counters = {key: 0 for key in self.ppe_keys}
        self.actual_latest_states = {key: False for key in self.ppe_keys}
        self.override_active = False
        self.override_seconds_left = 0
        self.is_settings_visible = False
        self.is_help_visible = False
        self.first_dispense_done = False

        # --- Determine Default ESP32 Port based on OS ---
        if platform.system() == "Windows":
            self.esp32_port_name = "COM9"
        elif platform.system() == "Linux":
            self.esp32_port_name = "/dev/ttyUSB0"
        else:
            self.esp32_port_name = None # Or some other default/fallback
        print(f"Default ESP32 Port for {platform.system()}: {self.esp32_port_name}")

        self.esp32_serial = None    # Serial connection object

        # --- Window Setup ---
        self.setWindowTitle(f"PPE Vending Machine {version}")
        self.setMinimumSize(1024, 600)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowSystemMenuHint |
                          Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint |
                          Qt.WindowCloseButtonHint)
        # Centering is best handled by the OS or showMaximized()

        # --- UI Construction --- #
        central_widget = QWidget()
        central_widget.setStyleSheet("QWidget { background-color: #F0F0F0; }") # Basic light background
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        self.stacked_widget = QWidget()
        self.main_stacked_layout = QHBoxLayout(self.stacked_widget)
        self.main_stacked_layout.setSpacing(20)
        self.main_stacked_layout.setContentsMargins(0, 0, 0, 0)

        # Create pages
        main_content = self._create_main_content_widget()
        self.settings_widget = self._create_settings_widget()
        self.help_widget = self._create_help_widget()

        # Add pages to stacked layout
        self.main_stacked_layout.addWidget(main_content)
        self.main_stacked_layout.addWidget(self.settings_widget)
        self.main_stacked_layout.addWidget(self.help_widget)
        main_layout.addWidget(self.stacked_widget)

        # Initial visibility state
        self.settings_widget.hide()
        self.help_widget.hide()

        # --- Timers --- #
        self.override_timer = QTimer(self)
        self.override_timer.timeout.connect(self.update_override_countdown)

        # --- Detection Thread --- #
        self._start_detection_thread()

        # Attempt initial ESP32 connection using the default port
        self._connect_to_esp32()

    # === Helper Methods for UI Creation ===

    def _create_main_content_widget(self):
        """Creates the main content widget holding header, status, camera/buttons."""
        main_content = QWidget()
        layout = QVBoxLayout(main_content)
        layout.setSpacing(15)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addLayout(self._create_header())
        layout.addWidget(self._create_status_frame())
        layout.addLayout(self._create_camera_button_section(), 1)

        return main_content

    def _create_header(self):
        """Creates the header layout with Help, Title, Settings buttons."""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 15)

        self.help_button = QPushButton("Help")
        self.help_button.setFixedSize(100, 40)
        self.help_button.setStyleSheet(self._get_button_style_nav())
        self.help_button.clicked.connect(self.toggle_help)

        self.title = QLabel("PPE Vending Machine")
        self.title.setFont(QFont('Arial', 28, QFont.Bold))
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet(f"color: {self.secondary_color};") # Initializing color

        self.settings_button = QPushButton("Settings")
        self.settings_button.setFixedSize(100, 40)
        self.settings_button.setStyleSheet(self._get_button_style_nav())
        self.settings_button.clicked.connect(self.toggle_settings)

        layout.addWidget(self.help_button)
        layout.addStretch(1)
        layout.addWidget(self.title)
        layout.addStretch(1)
        layout.addWidget(self.settings_button)
        return layout

    def _create_status_frame(self):
        """Creates the status frame containing gate and dispensing labels."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        frame.setStyleSheet("QFrame { background-color: white; border-radius: 12px; padding: 8px; }")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(15, 10, 15, 10)

        self.gate_status = QLabel("Gate LOCKED")
        self.gate_status.setFont(QFont('Arial', 16, QFont.Bold))
        self._set_gate_style_locked()

        self.dispensing_status = QLabel("Ready to dispense...")
        self.dispensing_status.setFont(QFont('Arial', 16))
        self.dispensing_status.setStyleSheet("QLabel { color: #8E8E93; padding: 8px; background-color: #F8F9FA; border-radius: 8px; }")

        layout.addWidget(self.gate_status)
        layout.addStretch(1)
        layout.addWidget(self.dispensing_status)
        return frame

    def _create_camera_button_section(self):
        """Creates the horizontal layout for camera feed and button grid."""
        layout = QHBoxLayout()
        layout.setSpacing(20)

        self.camera_feed = QLabel("Camera Feed")
        self.camera_feed.setMinimumSize(CAMERA_FEED_WIDTH, CAMERA_FEED_HEIGHT)
        self.camera_feed.setStyleSheet("QLabel { border: 2px solid #E1E1E1; background-color: #2C3E50; border-radius: 12px; padding: 4px; color: white; }")
        self.camera_feed.setAlignment(Qt.AlignCenter)

        button_grid_widget = self._create_button_grid()

        layout.addWidget(self.camera_feed, 2)
        layout.addWidget(button_grid_widget, 1)
        return layout

    def _create_button_grid(self):
        """Creates the widget containing the grid of PPE/Override buttons."""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)

        buttons_config = [
            ("Hard Hat", "hardhat", 0, 0),
            ("Hi-Vis Vest", "vest", 0, 1),
            ("Gloves", "gloves", 1, 0),
            ("Safety Glasses", "glasses", 1, 1),
            ("Ear Plugs", "earplugs", 2, 0),
            ("OVERRIDE", "override", 2, 1)
        ]

        self.ppe_buttons = {}
        for label, key, row, col in buttons_config:
            button = QPushButton(label)
            button.setFixedSize(BUTTON_WIDTH, BUTTON_HEIGHT)

            if key == "override":
                button.setStyleSheet(self._get_button_style_override())
                button.clicked.connect(self.override_dispense)
            else:
                button.setStyleSheet(self._get_button_style(self.danger_color, "#CC2A25", "#B32620")) # Initial Red
                button.clicked.connect(lambda checked=False, k=key: self.dispense_item(k))

            grid_layout.addWidget(button, row, col)
            self.ppe_buttons[key] = button

        container_layout.addStretch(1)
        container_layout.addLayout(grid_layout)
        container_layout.addStretch(1)
        return container

    def _create_settings_widget(self):
        """Creates the settings page widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        title = QLabel("Settings")
        title.setFont(QFont('Arial', 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("QLabel { color: #2C3E50; padding: 15px; }")

        form_container = QFrame()
        form_container.setStyleSheet("QFrame { background-color: #F8F9FA; border-radius: 12px; padding: 15px; } QLabel { color: #2C3E50; font-size: 14px; font-weight: bold; }")
        form_layout = QVBoxLayout(form_container)

        # --- AVend Settings ---
        avend_group_box = QFrame()
        avend_layout = QVBoxLayout(avend_group_box)
        avend_layout.setContentsMargins(0, 0, 0, 0)
        avend_title = QLabel("AVend Connection")
        avend_title.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 8px;")
        avend_layout.addWidget(avend_title)

        ip_port_widget = QWidget()
        ip_port_row_layout = QHBoxLayout(ip_port_widget)
        ip_port_row_layout.setContentsMargins(0,0,0,0)
        ip_port_row_layout.setSpacing(8)

        ip_label = QLabel("AVend IP:")
        self.avend_ip_input = QLineEdit(DEFAULT_AVEND_IP)
        self.avend_ip_input.setPlaceholderText("IP address")
        self.avend_ip_input.setStyleSheet("QLineEdit { padding: 10px; border: 1px solid #E1E1E1; border-radius: 6px; font-size: 14px; background-color: white; color: #2C3E50; } QLineEdit:focus { border-color: #007AFF; }")

        port_label = QLabel("Port:")
        self.avend_port_input = QLineEdit(DEFAULT_AVEND_PORT)
        self.avend_port_input.setPlaceholderText("Port")
        self.avend_port_input.setFixedWidth(70)
        self.avend_port_input.setStyleSheet("QLineEdit { padding: 10px; border: 1px solid #E1E1E1; border-radius: 6px; font-size: 14px; background-color: white; color: #2C3E50; } QLineEdit:focus { border-color: #007AFF; }")

        ip_port_row_layout.addWidget(ip_label)
        ip_port_row_layout.addWidget(self.avend_ip_input)
        ip_port_row_layout.addWidget(port_label)
        ip_port_row_layout.addWidget(self.avend_port_input)
        avend_layout.addWidget(ip_port_widget)

        # --- ESP32 Settings ---
        esp32_group_box = QFrame()
        esp32_layout = QVBoxLayout(esp32_group_box)
        esp32_layout.setContentsMargins(0, 10, 0, 0)
        esp32_title = QLabel("Gate Controller (ESP32)")
        esp32_title.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 8px;")
        esp32_layout.addWidget(esp32_title)

        esp32_port_widget = QWidget()
        esp32_port_layout = QHBoxLayout(esp32_port_widget)
        esp32_port_layout.setContentsMargins(0, 0, 0, 0)
        esp32_port_layout.setSpacing(8)

        esp32_label = QLabel("COM Port:")
        self.esp32_port_input = QLineEdit()
        # Set initial text based on the determined default port
        if self.esp32_port_name:
            self.esp32_port_input.setText(self.esp32_port_name)
        else:
            self.esp32_port_input.setPlaceholderText("e.g., COM3 or /dev/ttyUSB0")
        self.esp32_port_input.setStyleSheet("QLineEdit { padding: 10px; border: 1px solid #E1E1E1; border-radius: 6px; font-size: 14px; background-color: white; color: #2C3E50; } QLineEdit:focus { border-color: #007AFF; }")

        esp32_port_layout.addWidget(esp32_label)
        esp32_port_layout.addWidget(self.esp32_port_input, 1)
        esp32_layout.addWidget(esp32_port_widget)

        # Add widgets to form container
        form_layout.addWidget(avend_group_box)
        form_layout.addWidget(esp32_group_box)
        form_layout.addSpacing(15)

        # Save Button
        self.save_settings_btn = QPushButton("Save Settings")
        self.save_settings_btn.setStyleSheet(self._get_button_style_nav())
        self.save_settings_btn.setMinimumWidth(130)
        self.save_settings_btn.clicked.connect(self.save_settings)
        form_layout.addWidget(self.save_settings_btn, alignment=Qt.AlignCenter)

        # Add widgets to main settings layout
        layout.addWidget(title)
        layout.addWidget(form_container)
        layout.addStretch(1)
        return widget

    def _create_help_widget(self):
        """Creates the help page widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Help")
        title.setFont(QFont('Arial', 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("QLabel { color: #2C3E50; padding: 3px; }")

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont('Arial', 12))
        text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        text_edit.setStyleSheet("QTextEdit { background-color: white; border-radius: 12px; padding: 8px 5px; color: #2C3E50; }")
        help_content = """
            PPE Detection:
            • The AI detects required PPE using the camera.
            • Rotate your head slightly to ensure all PPE is visible.
            • Green buttons indicate detected PPE; red buttons indicate missing PPE.

            Dispensing PPE:
            • Click on the PPE item to dispense if you do not have it.
            • The safety gate will remain locked until all required PPE is detected.

            Safety Override:
            • Use the orange OVERRIDE button for emergency or administrative overrides.
            • It will open the safety gate.
        """
        text_edit.setText(help_content.strip())

        # Back button
        button_container = QWidget()
        button_layout = QVBoxLayout(button_container)
        button_layout.setContentsMargins(0, 10, 0, 0)
        back_button = QPushButton("Back to Main Screen")
        back_button.setFixedSize(180, 40)
        back_button.setStyleSheet(self._get_button_style_nav())
        back_button.clicked.connect(self.toggle_help)
        button_layout.addWidget(back_button, 0, Qt.AlignCenter)

        layout.addWidget(title, 0)
        layout.addWidget(text_edit, 1)
        layout.addWidget(button_container, 0)
        return widget

    # === Dynamic Styling Helpers ===
    def _get_button_style(self, bg_color, hover_color, pressed_color):
        """Generates QSS for standard PPE buttons (Red/Green)."""
        return f"""
            QPushButton {{
                background-color: {bg_color}; color: white;
                border-radius: 12px; font-size: 18px; font-weight: bold;
                border: none; padding: 12px; margin: 4px;
            }}
            QPushButton:hover {{ background-color: {hover_color}; padding: 10px; margin: 6px; }}
            QPushButton:pressed {{ background-color: {pressed_color}; padding: 12px; margin: 4px; }}
        """

    def _get_button_style_override(self):
        """Generates QSS for the Override button."""
        return f"""
            QPushButton {{
                background-color: {self.secondary_color}; color: white;
                border-radius: 12px; font-size: 20px; font-weight: bold;
                text-transform: uppercase; border: none; padding: 12px; margin: 4px;
            }}
            QPushButton:hover {{ background-color: #E59400; padding: 10px; margin: 6px; }}
            QPushButton:pressed {{ background-color: #CC8400; padding: 12px; margin: 4px; }}
        """

    def _get_button_style_nav(self, bg_color=None, hover_color=None, pressed_color=None):
        """Generates QSS for navigation buttons (Help, Settings, Back, Save)."""
        bg = bg_color or self.nav_color
        hover = hover_color or self.nav_hover_color
        pressed = pressed_color or self.nav_pressed_color
        return f"""
            QPushButton {{
                background-color: {bg}; color: white;
                border-radius: 10px; font-size: 16px; font-weight: bold;
                border: none; padding: 10px; margin: 3px;
            }}
            QPushButton:hover {{ background-color: {hover}; padding: 8px; margin: 5px; }}
            QPushButton:pressed {{ background-color: {pressed}; padding: 10px; margin: 3px; }}
        """

    def _set_gate_style_locked(self):
        """Sets the gate status label style to LOCKED."""
        self.gate_status.setStyleSheet(f"""
            QLabel {{ color: {self.danger_color}; background-color: #FFE5E5; padding: 8px; border-radius: 8px; font-weight: bold; }}
        """)

    def _set_gate_style_unlocked(self):
        """Sets the gate status label style to UNLOCKED (or Override)."""
        self.gate_status.setStyleSheet(f"""
            QLabel {{ color: white; background-color: {self.success_color}; padding: 8px; border-radius: 8px; font-weight: bold; }}
        """)

    # === Threading ===
    def _start_detection_thread(self):
        """Initializes and starts the background detection thread."""
        print("Starting Detection Thread...")
        self.detection_thread = DetectionThread()
        # Connect signals to slots
        self.detection_thread.detection_signal.connect(self.update_button_states_and_boxes)
        self.detection_thread.camera_status_signal.connect(self.update_camera_status)
        self.detection_thread.frame_signal.connect(self.update_camera_feed)
        self.detection_thread.start()

    # === Serial Communication Helpers ===

    def _connect_to_esp32(self):
        """Attempts to connect to the ESP32 on the configured COM port."""
        if self.esp32_serial and self.esp32_serial.is_open:
            print("ESP32 serial port already open.")
            return True

        if not self.esp32_port_name:
            print("ESP32 COM port not configured in settings.")
            return False

        try:
            print(f"Attempting to connect to ESP32 on {self.esp32_port_name}...")
            # Close previous connection if it exists but isn't open
            if self.esp32_serial:
                self.esp32_serial.close()

            self.esp32_serial = serial.Serial(
                port=self.esp32_port_name,
                baudrate=115200, # Match ESP32 code
                timeout=1,       # Read timeout
                write_timeout=1  # Write timeout
            )
            # Wait briefly for connection to establish
            time.sleep(2) # Recommended after opening serial
            if self.esp32_serial.is_open:
                print(f"Successfully connected to ESP32 on {self.esp32_port_name}.")
                self._send_to_esp32("lock") # Send initial lock command
                return True
            else:
                print(f"Failed to open ESP32 serial port {self.esp32_port_name} (is_open is False).")
                self.esp32_serial = None # Clear if connection failed
                return False
        except serial.SerialException as e:
            print(f"ERROR connecting to ESP32 on {self.esp32_port_name}: {e}")
            QMessageBox.warning(self, "ESP32 Connection Error", f"Could not connect to {self.esp32_port_name}.\nError: {e}\n\nPlease check the port name and ensure the device is paired/connected.")
            self.esp32_serial = None # Clear if connection failed
            return False
        except Exception as e:
            print(f"Unexpected ERROR during ESP32 connection: {e}")
            QMessageBox.critical(self, "ESP32 Error", f"An unexpected error occurred during ESP32 connection: {e}")
            self.esp32_serial = None # Clear if connection failed
            return False

    def _send_to_esp32(self, command):
        """Sends a command string to the connected ESP32."""
        if not self.esp32_serial or not self.esp32_serial.is_open:
            print(f"ESP32 not connected. Cannot send command: '{command}'")
            # Attempt to reconnect?
            # if not self._connect_to_esp32():
            #     QMessageBox.warning(self, "ESP32 Error", "Cannot send command: ESP32 is not connected.")
            #     return
            # else: # Reconnect successful, try sending again
            #      pass # Continue to send below
            return # For now, just return if not connected

        try:
            command_bytes = f"{command}\n".encode('utf-8')
            print(f"Sending to ESP32: {command_bytes.decode().strip()}")
            self.esp32_serial.write(command_bytes)
            self.esp32_serial.flush() # Ensure data is sent
            # Optionally read response? The ESP32 sends back confirmations.
            # response = self.esp32_serial.readline().decode('utf-8').strip()
            # if response:
            #     print(f"ESP32 Response: {response}")
            # else:
            #     print("ESP32: No response within timeout.")
        except serial.SerialTimeoutException:
            print(f"ERROR sending '{command}' to ESP32: Write timeout.")
            QMessageBox.warning(self, "ESP32 Communication Error", "Write timed out while sending command to ESP32.")
        except serial.SerialException as e:
            print(f"ERROR sending '{command}' to ESP32: {e}")
            QMessageBox.warning(self, "ESP32 Communication Error", f"Serial error sending command to ESP32: {e}")
            # Consider closing the port on error
            # self.esp32_serial.close()
            # self.esp32_serial = None
        except Exception as e:
            print(f"Unexpected ERROR sending '{command}' to ESP32: {e}")
            QMessageBox.critical(self, "ESP32 Error", f"An unexpected error occurred sending command to ESP32: {e}")

    # === Event Handlers / Slots ===
    @Slot(dict)
    def update_button_states_and_boxes(self, detection_payload):
        """
        Updates button colors based on detection states (with persistence)
        and stores the latest bounding box data.

        Args:
            detection_payload (dict): Dictionary containing 'states' and 'boxes'.
        """
        if self.override_active: return # Ignore updates during override

        if 'states' in detection_payload:
            latest_states = detection_payload['states']
            self.actual_latest_states = latest_states

            for key, button in self.ppe_buttons.items():
                if key == 'override': continue
                if key not in self.ppe_missing_counters: continue # Should not happen

                if key in latest_states and latest_states[key]: # Detected
                    self.ppe_missing_counters[key] = 0
                    button.setStyleSheet(self._get_button_style(self.success_color, "#2CB14F", "#248F3F")) # GREEN
                else: # Not Detected / Key missing
                    self.ppe_missing_counters[key] += 1
                    if self.ppe_missing_counters[key] >= MISS_THRESHOLD:
                        button.setStyleSheet(self._get_button_style(self.danger_color, "#CC2A25", "#B32620")) # RED
        else:
            print("Warning: 'states' key missing from detection payload.")

        if 'boxes' in detection_payload:
             self.latest_received_boxes = detection_payload['boxes']
        # else: keep previous boxes if key is missing

    @Slot(object)
    def update_camera_status(self, is_connected):
        """Updates the main title color based on camera connection status."""
        print(f"\nCamera Status Update: {is_connected}")
        text_to_set = "Camera Feed"
        color_to_set = self.secondary_color # Default/Warning color

        if is_connected is None:
            text_to_set = "Initializing camera..."
        elif is_connected:
            color_to_set = self.success_color
            text_to_set = "Camera connected..."
        else:
            text_to_set = "Camera not available"

        self.title.setStyleSheet(f"color: {color_to_set};")
        # Update camera feed text only if needed
        if self.camera_feed.text() != text_to_set and not (is_connected and not self.camera_feed.text()):
            self.camera_feed.setText(text_to_set)

    @Slot(QImage)
    def update_camera_feed(self, q_image):
        """Updates the camera feed display with the latest frame and boxes."""
        try:
            if q_image is None or q_image.isNull(): return

            label_width = self.camera_feed.width()
            label_height = self.camera_feed.height()
            if label_width <= 0 or label_height <= 0: return

            img_width = q_image.width()
            img_height = q_image.height()
            if img_width == 0 or img_height == 0: return

            # --- Scaling --- #
            final_pixmap_width = img_width
            final_pixmap_height = img_height
            src_aspect = img_width / img_height
            dst_aspect = label_width / label_height
            if src_aspect > dst_aspect:
                 final_pixmap_width = label_width
                 final_pixmap_height = int(final_pixmap_width / src_aspect)
            else:
                 final_pixmap_height = label_height
                 final_pixmap_width = int(final_pixmap_height * src_aspect)

            pixmap = QPixmap.fromImage(q_image).scaled(
                final_pixmap_width, final_pixmap_height,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )

            # --- Draw Bounding Boxes --- #
            if self.latest_received_boxes:
                 original_w, original_h = self.detection_resolution
                 if original_w > 0 and original_h > 0: # Avoid division by zero
                     scale_x = pixmap.width() / original_w
                     scale_y = pixmap.height() / original_h

                     painter = QPainter(pixmap)
                     pen = QPen(Qt.green, 2)
                     painter.setPen(pen)
                     painter.setFont(QFont('Arial', 8))

                     for box_data in self.latest_received_boxes:
                          try:
                              coords = box_data['coords']
                              label = box_data['label']
                              confidence = box_data['conf']
                              x1, y1, x2, y2 = [int(c) for c in coords]
                              scaled_x = int(x1 * scale_x)
                              scaled_y = int(y1 * scale_y)
                              scaled_w = int((x2 - x1) * scale_x)
                              scaled_h = int((y2 - y1) * scale_y)
                              painter.drawRect(scaled_x, scaled_y, scaled_w, scaled_h)
                              label_text = f"{label} ({confidence:.2f})"
                              painter.drawText(scaled_x, scaled_y - 5, label_text)
                          except KeyError as ke:
                               print(f"Error drawing box: Key missing {ke} in {box_data}")
                          except Exception as draw_e:
                               print(f"Error drawing box {box_data}: {draw_e}")
                     painter.end()
                 else:
                      print("Warning: Invalid detection_resolution for scaling boxes.")

            # --- Display Pixmap --- #
            # Ensure background is set correctly if label was showing text
            if self.camera_feed.text():
                self.camera_feed.setStyleSheet("QLabel { background-color: black; border-radius: 15px; }")
                self.camera_feed.setText("")
            self.camera_feed.setPixmap(pixmap)

        except Exception as e:
            print(f"\nError in update_camera_feed: {type(e).__name__}: {e}")
            traceback.print_exc()

    def dispense_item(self, item_key):
        """Handles dispensing a specific item."""
        if item_key in self.avend_codes:
            avend_code = self.avend_codes[item_key]
            item_name = self.item_names.get(item_key, item_key)
            self.dispensing_status.setText(f"Requesting {item_name} ({avend_code})...")
            self.dispensing_status.setStyleSheet(f"color: {self.secondary_color};")
            self.dispense_with_code(avend_code)
        else:
            QMessageBox.warning(self, "Dispense Error", f"No AVend code mapped for {item_key}")

    def override_dispense(self):
        """Handles the Override button action: temporary unlock and state change."""
        if self.override_active: return

        print("OVERRIDE ACTIVATED")
        self._send_to_esp32("unlock") # <<< Send unlock command to ESP32

        self.override_active = True
        self.override_seconds_left = OVERRIDE_DURATION_MS // 1000 # Use constant

        # Set buttons green
        green_style = self._get_button_style(self.success_color, "#2CB14F", "#248F3F")
        for key, button in self.ppe_buttons.items():
            if key != 'override':
                button.setStyleSheet(green_style)

        # Start countdown and timer
        self.update_override_countdown()
        self.override_timer.start(1000)

    @Slot()
    def update_override_countdown(self):
        """Slot connected to the override timer's timeout signal."""
        if self.override_seconds_left > 0:
            self.gate_status.setText(f"Gate UNLOCKED (Override: {self.override_seconds_left}s)")
            self._set_gate_style_unlocked()
            self.override_seconds_left -= 1
        else:
            self.override_timer.stop()
            print("Override countdown finished. Resetting state.")
            self.reset_override_state()

    def reset_override_state(self):
        """Resets the UI and state after the override period ends."""
        print("Resetting override state...")
        self._send_to_esp32("lock") # <<< Send lock command to ESP32

        self.override_active = False
        self.gate_status.setText("Gate LOCKED")
        self._set_gate_style_locked()
        # Re-apply actual button states
        self.update_button_states_and_boxes({
            'states': self.actual_latest_states,
            'boxes': self.latest_received_boxes
        })

    def dispense_with_code(self, code):
        """Handles the AVend API interaction for dispensing an item."""
        session_response = self.api.start_session()
        if not session_response.get("success", False):
            # Error handling for session start
            self.dispensing_status.setText(f"Error: Start Session Failed")
            self.dispensing_status.setStyleSheet(f"color: {self.danger_color};")
            QTimer.singleShot(STATUS_RESET_DELAY_MS, self.reset_status)
            return

        dispense_response = self.api.dispense(code=code)
        if dispense_response.get("success", False):
            # Don't show success message here - was removed by user
            # self.dispensing_status.setText(f"Successfully dispensed {code}")
            # self.dispensing_status.setStyleSheet(f"color: {self.success_color};")

            if not self.first_dispense_done:
                self.first_dispense_done = True
                self.call_h1_service()
        else:
            error_msg = dispense_response.get('error', 'Dispense failed')
            self.dispensing_status.setText(f"Error: {error_msg} ({code})")
            self.dispensing_status.setStyleSheet(f"color: {self.danger_color};")

        # Reset status label after a delay in both success/failure cases
        QTimer.singleShot(STATUS_RESET_DELAY_MS, self.reset_status)

    def call_h1_service(self):
        """Initiates the H1 service routine sequence (console log only)."""
        try:
            print(f"H1 Service routine check will start in {H1_SERVICE_DELAY_MS / 1000}s (console log only)")
            QTimer.singleShot(H1_SERVICE_DELAY_MS, self._start_h1_service_routine)
        except Exception as e:
            print(f"Exception setting up H1 Service routine: {str(e)}")

    def _start_h1_service_routine(self):
        """Calls the AVend API to start the H1 service routine (console log only)."""
        try:
            service_response = self.api.start_service_routine()
            if service_response.get("success", False):
                print("Successfully started H1 Service routine (running every 20s - console log only)")
            else:
                 print(f"Error starting H1 Service routine: {service_response.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"Exception running H1 Service routine: {str(e)}")

    def reset_status(self):
        """Resets the dispensing status label to default, avoiding override."""
        if not self.override_active:
             self.dispensing_status.setText("Ready to dispense...")
             self.dispensing_status.setStyleSheet("QLabel { color: #8E8E93; padding: 8px; background-color: #F8F9FA; border-radius: 8px; }")

    def toggle_help(self):
        """Shows/Hides the Help page and updates nav button styles."""
        active_style = self._get_button_style_nav(bg_color=self.nav_active_color)
        inactive_style = self._get_button_style_nav()
        if self.is_help_visible:
            self.help_widget.hide()
            self.main_stacked_layout.itemAt(0).widget().show()
            self.help_button.setStyleSheet(inactive_style)
        else:
            if self.is_settings_visible:
                self.settings_widget.hide()
                self.settings_button.setStyleSheet(inactive_style)
                self.is_settings_visible = False
            self.main_stacked_layout.itemAt(0).widget().hide()
            self.help_widget.show()
            self.help_button.setStyleSheet(active_style)
        self.is_help_visible = not self.is_help_visible

    def toggle_settings(self):
        """Shows/Hides the Settings page and updates nav button styles."""
        active_style = self._get_button_style_nav(bg_color=self.nav_active_color)
        inactive_style = self._get_button_style_nav()
        if self.is_settings_visible:
            self.settings_widget.hide()
            self.main_stacked_layout.itemAt(0).widget().show()
            self.settings_button.setStyleSheet(inactive_style)
        else:
            if self.is_help_visible:
                self.help_widget.hide()
                self.help_button.setStyleSheet(inactive_style)
                self.is_help_visible = False
            self.main_stacked_layout.itemAt(0).widget().hide()
            self.settings_widget.show()
            self.settings_button.setStyleSheet(active_style)
        self.is_settings_visible = not self.is_settings_visible

    def save_settings(self):
        """Saves AVend IP/Port and ESP32 COM port settings and reinitializes connections."""
        # AVend Settings
        host = self.avend_ip_input.text()
        port_str = self.avend_port_input.text()
        avend_saved = False
        try:
            port = int(port_str)
            if not (0 < port < 65536):
                 raise ValueError("Port number out of range")
            self.api = AvendAPI(host=host, port=port)
            print(f"AVend API settings saved and reinitialized: {host}:{port}")
            avend_saved = True
        except ValueError as ve:
            QMessageBox.warning(self, "Settings Error", f"Invalid AVend port number: {port_str}. {ve}")
        except Exception as e:
            QMessageBox.critical(self, "Settings Error", f"Failed to save AVend settings or reinitialize API: {str(e)}")

        # ESP32 Settings
        esp32_port = self.esp32_port_input.text().strip()
        esp32_connected = False
        if esp32_port:
            self.esp32_port_name = esp32_port
            print(f"ESP32 COM Port set to: {self.esp32_port_name}")
            # Attempt to connect immediately after saving
            esp32_connected = self._connect_to_esp32()
        else:
            print("ESP32 COM Port cleared.")
            self.esp32_port_name = None
            if self.esp32_serial and self.esp32_serial.is_open:
                self.esp32_serial.close()
                print("Closed existing ESP32 serial connection.")
            self.esp32_serial = None

        # Feedback and close settings view
        if avend_saved:
             if esp32_port and not esp32_connected:
                  QMessageBox.information(self, "Settings Saved", f"AVend settings saved for {host}:{port}.\nFailed to connect to ESP32 on {esp32_port}.")
             elif esp32_port and esp32_connected:
                  QMessageBox.information(self, "Settings Saved", f"AVend settings saved for {host}:{port}.\nSuccessfully connected to ESP32 on {esp32_port}.")
             else:
                  QMessageBox.information(self, "Settings Saved", f"AVend settings saved for {host}:{port}. ESP32 port not set.")
             self.toggle_settings() # Return to main view only if AVend settings were valid
        # else: Keep settings view open if AVend settings were invalid

    def closeEvent(self, event):
        """Handles the window close event, ensuring threads and connections are stopped."""
        print("Close event triggered. Stopping threads and connections...")
        # Stop Detection Thread
        if hasattr(self, 'detection_thread') and self.detection_thread.isRunning():
            self.detection_thread.stop()
            if not self.detection_thread.wait(5000):
                 print("Warning: Detection thread did not stop gracefully. Terminating.")
                 self.detection_thread.terminate()
                 self.detection_thread.wait()
            print("Detection thread stopped.")

        # Stop Override Timer
        if hasattr(self, 'override_timer') and self.override_timer.isActive():
            self.override_timer.stop()
            print("Override timer stopped.")

        # Stop H1 Service (if applicable)
        if hasattr(self, 'api') and hasattr(self.api, 'stop_service_routine'):
            try:
                 if callable(self.api.stop_service_routine):
                     self.api.stop_service_routine()
                     print("H1 Service routine stopped.")
            except Exception as e:
                print(f"Error stopping H1 Service routine: {str(e)}")

        # Close Serial Port
        if hasattr(self, 'esp32_serial') and self.esp32_serial and self.esp32_serial.is_open:
            try:
                print(f"Closing ESP32 serial port {self.esp32_port_name}...")
                # Maybe send a final 'lock' command?
                # self._send_to_esp32("lock")
                # time.sleep(0.1)
                self.esp32_serial.close()
                print("ESP32 serial port closed.")
            except serial.SerialException as e:
                print(f"Error closing ESP32 serial port: {e}")
            except Exception as e:
                print(f"Unexpected error closing ESP32 serial port: {e}")

        super().closeEvent(event)

# === Main Execution ===
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized() # Show maximized
    sys.exit(app.exec()) 