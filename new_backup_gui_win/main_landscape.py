# Import all the same dependencies as main.py
import sys
import os
import time
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QGridLayout,
                             QLineEdit, QMessageBox, QFrame, QFormLayout, QTextEdit)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QPalette, QColor, QImage, QPixmap, QPainter, QPen
import cv2 # Import cv2 here
import torch # Import torch here
import threading # Import threading here
import platform # Import platform here

# Import AVend API if available, otherwise create a mock
try:
    # Add parent directory to path to find avend_api_client
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(parent_dir)
    from avend_api_client.avend_api import AvendAPI
except ImportError:
    # Create a mock AvendAPI class if the real one isn't available
    class AvendAPI:
        def __init__(self, host="127.0.0.1", port=8080):
            self.base_url = f"http://{host}:{port}/avend"
            print(f"Mock AvendAPI initialized with {self.base_url}")
            
        def start_session(self):
            print("Mock: Starting session")
            return {"success": True, "response": "Mock session started"}
            
        def dispense(self, code=None):
            print(f"Mock: Dispensing {code}")
            return {"success": True, "response": f"Mock dispensed {code}"}

# Try to import the detection model components
try:
    # Import helper functions and the run_detection function that returns the model/config
    from capstone_model import run_detection, try_open_camera, get_linux_cameras, print_camera_info
    HAS_DETECTION_MODEL = True
except ImportError as e:
    print(f"ERROR importing from capstone_model: {e}")
    HAS_DETECTION_MODEL = False
    # Define mock functions if import fails
    def run_detection(): return {'model': None} # Return dict with None model
    def try_open_camera(idx, **kwargs): return None
    def get_linux_cameras(): return []
    def print_camera_info(cap, idx): pass

class DetectionThread(QThread):
    detection_signal = Signal(dict) # Emits latest detection states AND boxes
    camera_status_signal = Signal(object) # Use object to allow None, True, False
    frame_signal = Signal(QImage) # Emits raw frames for display

    def __init__(self):
        super().__init__()
        self.is_running = True
        self.config = None
        self.model = None
        self.cap = None
        self.lock = threading.Lock()
        self.latest_states = {
            "hardhat": False,
            "glasses": False,
            "beardnet": False,
            "earplugs": False,
            "gloves": False
        } # Shared state, protected by lock
        self.latest_boxes = [] # Store the list of boxes from the last prediction
        self.prediction_running = False
        self._initial_camera_status_sent = False

    def _run_prediction(self, frame_copy):
        """Runs YOLO prediction in a separate thread."""
        # print("Starting prediction sub-thread...") # Debug
        # Initialize locals for THIS prediction run
        prediction_states = {key: False for key in self.latest_states}
        prediction_boxes = []
        device_to_use = 'cpu' # Default to CPU
        detection_summary = [] # For logging detections to terminal

        try:
            if self.model is None:
                 print("Prediction skipped: Model not loaded.")
                 # Ensure state reflects no detection if model is missing
                 with self.lock:
                    self.latest_states = prediction_states # All False
                    self.latest_boxes = prediction_boxes # Empty
                 return # Don't reset flag here, finally block will handle it

            # Determine device
            if torch.cuda.is_available():
                device_to_use = 'cuda:0'
            
            # Predict
            results = self.model.predict(frame_copy, conf=0.5, verbose=False, stream=True, device=device_to_use)
            
            # Process results
            processed_a_result = False
            for result in results:
                processed_a_result = True
                if result.boxes: # If detections found
                    for box in result.boxes:
                        class_index = int(box.cls)
                        confidence = float(box.conf) # Get confidence score
                        if self.model.names:
                            class_name = self.model.names[class_index].lower()
                            if class_name in self.config['class_map']:
                                button_key = self.config['class_map'][class_name]
                                prediction_states[button_key] = True # Update local state
                                try:
                                     coords = box.xyxy[0].cpu().numpy().astype(int)
                                     # Store coords, label, AND confidence
                                     prediction_boxes.append({'coords': coords.tolist(), 'label': class_name, 'conf': confidence}) 
                                     # Add to terminal summary
                                     detection_summary.append(f"{class_name} ({confidence:.2f})")
                                except Exception as e:
                                     print(f"Error processing box data: {e}")
                break # Process only first result from stream
                
            # Print detection summary to terminal if anything was found
            if detection_summary:
                 print(f"[Detection] Found: {', '.join(detection_summary)}")
            else:
                 # Optionally print if nothing was found above threshold
                 # print("[Detection] No objects found (conf > 0.5)")
                 pass 
                 
            # Update shared state AFTER processing
            with self.lock:
                self.latest_states = prediction_states
                self.latest_boxes = prediction_boxes
                
        except Exception as e:
            print(f"Error during prediction sub-thread: {e}")
            import traceback
            traceback.print_exc()
            # On error, explicitly clear the shared state to avoid staleness
            print("Clearing detection state due to prediction error.")
            with self.lock:
                self.latest_states = {key: False for key in self.latest_states}
                self.latest_boxes = []
        finally:
            # Ensure the prediction running flag is always reset
            with self.lock:
                self.prediction_running = False
            # print("Prediction sub-thread finished.") # Debug

    def run(self):
        """Main worker loop for reading frames and dispatching predictions."""
        # Initial setup
        try:
            self.config = run_detection() # Get model and config
            self.model = self.config.get('model')
            
            if self.model is None:
                print("DetectionThread: Model not loaded. Cannot run detection.")
                self.camera_status_signal.emit(None) # Indicate failure
                self._initial_camera_status_sent = True
                # Keep thread alive but do nothing, or exit? Let's exit for now.
                return 

            print("\nInitializing camera detection system in DetectionThread...")
            print("----------------------------------------")
            self.camera_status_signal.emit(None) # Signal initializing
            self._initial_camera_status_sent = True
            
            # --- Camera Opening Logic (copied from old _detection_worker) ---
            self.cap = None
            if platform.system() != "Windows":
                preferred_indices = [1, 2, 0] 
                for index in preferred_indices:
                    print(f"\n--- Trying camera index {index} ---")
                    self.cap = try_open_camera(index, max_retries=2, retry_delay=1.5)
                    if self.cap:
                        print(f"--- Successfully opened camera index {index} ---")
                        break
                if not self.cap:
                     print("\nFailed to open any preferred camera indices on Linux.")
            else:
                print("\n--- Trying external camera (index 1) ---")
                self.cap = try_open_camera(1, max_retries=3, retry_delay=1.5)
                if self.cap is None:
                    print("\n--- External camera failed, trying built-in camera (index 0) ---")
                    self.cap = try_open_camera(0, max_retries=2, retry_delay=1.0)
            
            # --- Check if camera opened --- 
            if self.cap is None or not self.cap.isOpened():
                print("\n############################################")
                print("FATAL: Failed to initialize ANY camera in DetectionThread.")
                print("############################################")
                self.camera_status_signal.emit(False) # Signal disconnected
                return # Exit thread if camera fails
            
            print("\nCamera setup complete. Starting detection loop...")
            self.camera_status_signal.emit(True) # Signal connected
            
            frame_count = 0
            fps_start_time = time.time()
            read_fps_start_time = time.time()
            fps_frame_count = 0
            read_frame_count = 0
            target_frame_time = 1.0 / self.config.get('display_fps', 30) # Target time per frame

            while self.is_running:
                loop_start_time = time.time()
                
                # --- Read Frame --- 
                ret, frame = self.cap.read()
                read_time = time.time() - loop_start_time
                
                if not ret:
                    print(f"Error reading frame (read took {read_time:.4f}s). Retrying...")
                    time.sleep(0.5) # Wait before retrying
                    continue
                
                read_frame_count += 1
                frame_count += 1
                fps_frame_count += 1
                
                # --- Emit Raw Frame --- 
                # Moved this emission earlier, before potentially heavy state emission
                if frame is not None:
                    try:
                        # Convert raw frame for GUI display
                        display_frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        h, w, ch = display_frame_rgb.shape
                        bytes_per_line = ch * w
                        qt_image = QImage(display_frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                        self.frame_signal.emit(qt_image)
                        # emit_success = True # Flag not strictly needed here
                    except Exception as e:
                         print(f"Error converting/emitting frame: {e}")

                # --- Emit Current States AND Boxes --- 
                try:
                    with self.lock:
                        # Combine states and boxes into one payload
                        payload = {
                            'states': self.latest_states.copy(),
                            'boxes': self.latest_boxes # Send the current list of boxes from last prediction
                        }
                    self.detection_signal.emit(payload)
                except Exception as e:
                    print(f"Error emitting detection payload: {e}")
                    
                # --- Dispatch Prediction (Non-Blocking) --- 
                detection_interval = self.config.get('detection_interval', 5)
                with self.lock:
                    pred_running = self.prediction_running # Check flag safely
                
                if frame_count % detection_interval == 0 and not pred_running:
                    try:
                        # Set flag before starting thread
                        with self.lock:
                             self.prediction_running = True
                        # print("Dispatching prediction thread...") # Debug
                        predict_thread = threading.Thread(target=self._run_prediction, args=(frame.copy(),), daemon=True)
                        predict_thread.start()
                    except Exception as e:
                        print(f"Error starting prediction thread: {e}")
                        # Reset flag if thread failed to start
                        with self.lock:
                             self.prediction_running = False
                            
                # --- FPS Logging --- 
                current_time = time.time()
                if current_time - fps_start_time >= 5.0: # Print every 5 seconds
                    loop_fps = fps_frame_count / (current_time - fps_start_time)
                    actual_read_fps = read_frame_count / (current_time - read_fps_start_time)
                    with self.lock:
                        pred_running_status = self.prediction_running
                    print(f"Stats (5s avg): Loop FPS: {loop_fps:.2f}, Read FPS: {actual_read_fps:.2f}, Last read: {read_time:.4f}s, Predicting: {pred_running_status}")
                    fps_frame_count = 0
                    read_frame_count = 0
                    fps_start_time = current_time
                    read_fps_start_time = current_time
                    
                # --- Loop Rate Control --- 
                # Aim for the display_fps rate
                loop_end_time = time.time()
                loop_duration = loop_end_time - loop_start_time
                sleep_time = max(0, target_frame_time - loop_duration)
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            # --- Cleanup --- 
            print("Exiting detection loop. Cleaning up camera resources...")
            if self.cap:
                self.cap.release()
            print("DetectionThread cleanup complete.")
            self.camera_status_signal.emit(False) # Final disconnect signal
            
        except Exception as e:
            print(f"\n--- CRITICAL ERROR IN DetectionThread RUN METHOD ---")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {str(e)}")
            import traceback
            traceback.print_exc()
            print("--------------------------------------------------")
            if not self._initial_camera_status_sent:
                 self.camera_status_signal.emit(None) # Ensure status is sent if error before loop
            else:
                 self.camera_status_signal.emit(False) # Signal disconnect due to error
            # Attempt cleanup even on error
            if self.cap and self.cap.isOpened():
                 self.cap.release()
                 print("Camera released after error.")

    def stop(self):
        print("DetectionThread stop called.")
        self.is_running = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PPE Vending Machine")
        # Set minimum size and allow maximization
        self.setMinimumSize(1024, 600)  # Landscape size as minimum
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | 
                          Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | 
                          Qt.WindowCloseButtonHint)
        
        # Initialize AVend API with default values
        self.api = AvendAPI()
        self.avend_codes = {
            "hardhat": "A1",
            "glasses": "A2",
            "beardnet": "A3",
            "earplugs": "A4",
            "gloves": "A5"
        }
        
        # Main color scheme
        self.primary_color = "#FF7B7B"
        self.secondary_color = "#FFA500"
        self.success_color = "#34C759"
        self.danger_color = "#FF3B30"
        
        # Center the window on screen
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        
        # Central widget and main layout
        central_widget = QWidget()
        central_widget.setStyleSheet("QWidget { background-color: #F0F0F0; }")
        self.setCentralWidget(central_widget)
        
        # Main horizontal layout for landscape orientation
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(30)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Create a stacked widget for main content and settings
        self.stacked_widget = QWidget()
        self.main_stacked_layout = QHBoxLayout(self.stacked_widget)
        self.main_stacked_layout.setSpacing(30)
        self.main_stacked_layout.setContentsMargins(0, 0, 0, 0)
        
        # Settings widget
        self.settings_widget = QWidget()
        settings_layout = QVBoxLayout(self.settings_widget)
        settings_layout.setSpacing(20)
        
        # Settings title
        settings_title = QLabel("Settings")
        settings_title.setFont(QFont('Arial', 24, QFont.Bold))
        settings_title.setAlignment(Qt.AlignCenter)
        settings_title.setStyleSheet("""
            QLabel {
                color: #2C3E50;
                padding: 20px;
            }
        """)
        
        # Settings form
        settings_form = QFormLayout()
        settings_form.setSpacing(15)
        settings_form.setContentsMargins(20, 20, 20, 20)
        
        # Form container with background
        form_container = QFrame()
        form_container.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border-radius: 15px;
                padding: 20px;
            }
            QLabel {
                color: #2C3E50;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        
        # AVend IP settings
        self.avend_ip_input = QLineEdit()
        self.avend_ip_input.setPlaceholderText("Enter AVend IP address")
        self.avend_ip_input.setText("127.0.0.1")  # Default IP
        self.avend_ip_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 2px solid #E1E1E1;
                border-radius: 8px;
                font-size: 16px;
                background-color: white;
                color: #2C3E50;
            }
            QLineEdit:focus {
                border-color: #007AFF;
            }
        """)
        
        # AVend Port settings
        self.avend_port_input = QLineEdit()
        self.avend_port_input.setPlaceholderText("Enter AVend Port")
        self.avend_port_input.setText("8080")  # Default port
        self.avend_port_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 2px solid #E1E1E1;
                border-radius: 8px;
                font-size: 16px;
                background-color: white;
                color: #2C3E50;
            }
            QLineEdit:focus {
                border-color: #007AFF;
            }
        """)
        
        # Save settings button
        self.save_settings_btn = QPushButton("Save Settings")
        self.save_settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border-radius: 10px;
                padding: 15px;
                font-size: 16px;
                font-weight: bold;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #0062CC;
            }
            QPushButton:pressed {
                background-color: #004999;
            }
        """)
        self.save_settings_btn.clicked.connect(self.save_settings)
        
        settings_form.addRow("AVend IP:", self.avend_ip_input)
        settings_form.addRow("AVend Port:", self.avend_port_input)
        
        # Add form to container
        form_container_layout = QVBoxLayout(form_container)
        form_container_layout.addLayout(settings_form)
        form_container_layout.addSpacing(20)
        form_container_layout.addWidget(self.save_settings_btn, alignment=Qt.AlignCenter)
        
        # Add everything to settings layout
        settings_layout.addWidget(settings_title)
        settings_layout.addWidget(form_container)
        settings_layout.addStretch(1)
        
        # Help content widget
        self.help_widget = QWidget()
        help_layout = QVBoxLayout(self.help_widget)
        help_layout.setSpacing(30)  # Increased spacing between elements
        help_layout.setContentsMargins(30, 30, 30, 30)  # Added margins around the entire layout
        
        # Help title
        help_title = QLabel("Help")
        help_title.setFont(QFont('Arial', 24, QFont.Bold))
        help_title.setAlignment(Qt.AlignCenter)
        help_title.setStyleSheet("QLabel { color: #2C3E50; padding: 20px; }")
        
        # Simple text edit for help content
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setFont(QFont('Arial', 14))
        help_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border-radius: 15px;
                padding: 20px;
                color: #2C3E50;
            }
        """)
        
        # Set the help content
        help_content = """PPE Detection:
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

        help_text.setText(help_content)
        
        # Back button with container for proper spacing
        button_container = QWidget()
        button_layout = QVBoxLayout(button_container)
        button_layout.setContentsMargins(0, 30, 0, 0)  # Add more top margin for spacing
        
        back_button = QPushButton("Back to Main Screen")
        back_button.setFixedSize(200, 50)
        back_button.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
                border: none;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #0062CC;
            }
            QPushButton:pressed {
                background-color: #004999;
            }
        """)
        back_button.clicked.connect(self.toggle_help)
        
        button_layout.addWidget(back_button, 0, Qt.AlignCenter)
        
        # Add everything to help layout with proper spacing
        help_layout.addWidget(help_title, 0)
        help_layout.addWidget(help_text, 1)
        help_layout.addWidget(button_container, 0)
        
        # Create main content widget
        main_content = QWidget()
        main_content_layout = QVBoxLayout(main_content)
        main_content_layout.setSpacing(20)
        main_content_layout.setContentsMargins(0, 0, 0, 0)

        # Header with title and buttons - now spans full width
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 20)  # Add bottom margin
        
        # Help button
        self.help_button = QPushButton("Help")
        self.help_button.setFixedSize(120, 50)
        self.help_button.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border-radius: 15px;
                font-size: 18px;
                font-weight: bold;
                border: none;
                padding: 10px;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #0062CC;
                padding: 8px;
                margin: 4px;
            }
            QPushButton:pressed {
                background-color: #004999;
                padding: 10px;
                margin: 2px;
            }
        """)
        self.help_button.clicked.connect(self.toggle_help)
        
        # Title
        self.title = QLabel("PPE Vending Machine")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setFont(QFont('Arial', 32, QFont.Bold))
        self.title.setStyleSheet("""
            QLabel {
                color: #2C3E50;
                padding: 10px;
                margin: 10px;
            }
        """)
        
        # Settings button
        self.settings_button = QPushButton("Settings")
        self.settings_button.setFixedSize(120, 50)
        self.settings_button.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border-radius: 15px;
                font-size: 18px;
                font-weight: bold;
                border: none;
                padding: 10px;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #0062CC;
                padding: 8px;
                margin: 4px;
            }
            QPushButton:pressed {
                background-color: #004999;
                padding: 10px;
                margin: 2px;
            }
        """)
        self.settings_button.clicked.connect(self.toggle_settings)
        
        header_layout.addWidget(self.help_button)
        header_layout.addStretch(1)
        header_layout.addWidget(self.title)
        header_layout.addStretch(1)
        header_layout.addWidget(self.settings_button)
        
        # Status section - now spans full width
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        status_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 15px;
                padding: 10px;
            }
        """)
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(20, 15, 20, 15)
        
        # Gate status
        self.gate_status = QLabel("Gate LOCKED")
        self.gate_status.setFont(QFont('Arial', 18, QFont.Bold))
        self.gate_status.setStyleSheet(f"""
            QLabel {{
                color: {self.danger_color};
                padding: 10px;
                background-color: #FFE5E5;
                border-radius: 10px;
            }}
        """)
        
        # Dispensing status
        self.dispensing_status = QLabel("Ready to dispense...")
        self.dispensing_status.setFont(QFont('Arial', 18))
        self.dispensing_status.setStyleSheet("""
            QLabel {
                color: #8E8E93;
                padding: 10px;
                background-color: #F8F9FA;
                border-radius: 10px;
            }
        """)
        
        status_layout.addWidget(self.gate_status)
        status_layout.addStretch(1)
        status_layout.addWidget(self.dispensing_status)

        # Content section (camera feed and buttons) - horizontal layout
        content_layout = QHBoxLayout()
        content_layout.setSpacing(30)
        
        # Camera feed
        self.camera_feed = QLabel()
        # Calculate size based on button dimensions plus spacing -> Change to fixed size
        # camera_width = 2 * 180 + 20  # 2 buttons wide + spacing
        # camera_height = 2 * 120 + 20  # 2 buttons high + spacing
        camera_width = 640 # Match capture width
        camera_height = 480 # Match capture height
        self.camera_feed.setMinimumSize(camera_width, camera_height)
        self.camera_feed.setStyleSheet("""
            QLabel {
                border: 3px solid #E1E1E1;
                background-color: #2C3E50;
                border-radius: 15px;
                padding: 5px;
                color: white;
            }
        """)
        self.camera_feed.setAlignment(Qt.AlignCenter)
        self.camera_feed.setText("Camera Feed")
        
        # Button grid
        button_grid = QGridLayout()
        button_grid.setSpacing(20)  # Increased spacing between buttons
        
        # Configure buttons
        buttons_config = [
            ("Hard Hat (A1)", "hardhat", 0, 0),
            ("Beard Net (A3)", "beardnet", 0, 1),
            ("Gloves (A5)", "gloves", 1, 0),
            ("Safety Glasses (A2)", "glasses", 1, 1),
            ("Ear Plugs (A4)", "earplugs", 2, 0),
            ("OVERRIDE", "override", 2, 1)
        ]
        
        self.ppe_buttons = {}
        for label, key, row, col in buttons_config:
            button = QPushButton(label)
            button.setFixedSize(180, 110)  # Reduced button size
            
            if key == "override":
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {self.secondary_color};
                        color: white;
                        border-radius: 12px;
                        font-size: 20px;
                        font-weight: bold;
                        text-transform: uppercase;
                        border: none;
                        padding: 12px;
                        margin: 4px;
                    }}
                    QPushButton:hover {{
                        background-color: #E59400;
                        padding: 10px;
                        margin: 6px;
                    }}
                    QPushButton:pressed {{
                        background-color: #CC8400;
                        padding: 12px;
                        margin: 4px;
                    }}
                """)
            else:
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {self.primary_color};
                        color: white;
                        border-radius: 12px;
                        font-size: 18px;
                        font-weight: bold;
                        border: none;
                        padding: 12px;
                        margin: 4px;
                    }}
                    QPushButton:hover {{
                        background-color: #FF6B6B;
                        padding: 10px;
                        margin: 6px;
                    }}
                    QPushButton:pressed {{
                        background-color: #FF5252;
                        padding: 12px;
                        margin: 4px;
                    }}
                """)
            
            if key == "override":
                button.clicked.connect(self.override_dispense)
            else:
                button.clicked.connect(lambda checked, k=key: self.dispense_item(k))
            
            button_grid.addWidget(button, row, col)
            self.ppe_buttons[key] = button

        # Add camera feed and button grid to content layout
        # Adjust stretch factors to give camera more space
        content_layout.addWidget(self.camera_feed, 3)  # Give camera feed 3/4 width (was 2)
        
        # Create a container for the button grid
        button_container = QWidget()
        button_container_layout = QVBoxLayout(button_container)
        button_container_layout.addStretch(1)
        button_container_layout.addLayout(button_grid)
        button_container_layout.addStretch(1)
        content_layout.addWidget(button_container, 1)  # Give buttons 1/4 width (was 1)

        # Add all sections to main content layout
        main_content_layout.addLayout(header_layout)
        main_content_layout.addWidget(status_frame)
        main_content_layout.addLayout(content_layout, 1)

        # Add widgets to stacked layout
        self.main_stacked_layout.addWidget(main_content)
        self.main_stacked_layout.addWidget(self.settings_widget)
        self.main_stacked_layout.addWidget(self.help_widget)
        
        # Add stacked widget to main layout
        main_layout.addWidget(self.stacked_widget)
        
        # Initialize with main content visible, others hidden
        self.settings_widget.hide()
        self.help_widget.hide()
        self.is_settings_visible = False
        self.is_help_visible = False
        
        # Start detection thread
        self.detection_thread = DetectionThread()
        self.detection_thread.detection_signal.connect(self.update_button_states_and_boxes)
        self.detection_thread.camera_status_signal.connect(self.update_camera_status)
        self.detection_thread.frame_signal.connect(self.update_camera_feed)
        self.detection_thread.start()

        # Flag to track if first manual dispense has been done
        self.first_dispense_done = False

        self.latest_received_boxes = [] # Store the latest boxes for drawing
        self.detection_resolution = (640, 480) # Store the resolution used for detection
        self.ppe_missing_counters = { # Counters for state persistence
            "hardhat": 0,
            "glasses": 0,
            "beardnet": 0,
            "earplugs": 0,
            "gloves": 0
        }
        self.MISS_THRESHOLD = 50 # Consecutive misses needed to turn button RED

    def update_button_states_and_boxes(self, detection_payload):
        """Update button colors with persistence AND store the latest bounding boxes."""
        # print(f"Received detection payload: {detection_payload}") # Verbose Debug
        
        # --- Update Button States with Persistence --- #
        if 'states' in detection_payload:
            latest_states = detection_payload['states']
            # print(f"Updating button states: {latest_states}") # Debug
            for key, button in self.ppe_buttons.items():
                if key == 'override': # Skip override button
                    continue

                if key in latest_states:
                    if latest_states[key]: # Item DETECTED in this cycle
                        self.ppe_missing_counters[key] = 0 # Reset miss counter
                        # Set button GREEN
                        button.setStyleSheet(f"""
                            QPushButton {{
                                background-color: {self.success_color};
                                color: white;
                                border-radius: 12px;
                                font-size: 18px;
                                font-weight: bold;
                                padding: 12px;
                                margin: 4px;
                            }}
                            QPushButton:hover {{
                                background-color: #2CB14F;
                                padding: 10px;
                                margin: 6px;
                            }}
                            QPushButton:pressed {{
                                background-color: #248F3F;
                                padding: 12px;
                                margin: 4px;
                            }}
                        """)
                    else: # Item NOT DETECTED in this cycle
                        self.ppe_missing_counters[key] += 1
                        # print(f" {key} miss count: {self.ppe_missing_counters[key]}") # Debug
                        # Only turn RED if missing threshold is met
                        if self.ppe_missing_counters[key] >= self.MISS_THRESHOLD:
                            # Set button RED
                            button.setStyleSheet(f"""
                                QPushButton {{
                                    background-color: {self.danger_color};
                                    color: white;
                                    border-radius: 12px;
                                    font-size: 18px;
                                    font-weight: bold;
                                    padding: 12px;
                                    margin: 4px;
                                }}
                                QPushButton:hover {{
                                    background-color: #CC2A25;
                                    padding: 10px;
                                    margin: 6px;
                                }}
                                QPushButton:pressed {{
                                    background-color: #B32620;
                                    padding: 12px;
                                    margin: 4px;
                                }}
                            """)
                else:
                    # Handle case where key is missing from states (shouldn't happen often)
                    # Option: Treat as a miss or keep current state? Let's treat as miss.
                    print(f"Warning: State for button key {key} not found in detection results. Incrementing miss counter.")
                    self.ppe_missing_counters[key] += 1
                    if self.ppe_missing_counters[key] >= self.MISS_THRESHOLD:
                        button.setStyleSheet(f"""
                            QPushButton {{
                                background-color: {self.danger_color};
                                color: white;
                                border-radius: 12px;
                                font-size: 18px;
                                font-weight: bold;
                                padding: 12px;
                                margin: 4px;
                            }}
                            QPushButton:hover {{
                                background-color: #CC2A25;
                                padding: 10px;
                                margin: 6px;
                            }}
                            QPushButton:pressed {{
                                background-color: #B32620;
                                padding: 12px;
                                margin: 4px;
                            }}
                        """) # Set Red if threshold met

        else:
            print("Warning: 'states' key not found in detection_payload")

        # --- Store latest boxes --- #
        if 'boxes' in detection_payload:
            # print(f"Received boxes: {detection_payload['boxes']}") # Debug
            self.latest_received_boxes = detection_payload['boxes']
        else:
            print("Warning: 'boxes' key not found in detection_payload")
            self.latest_received_boxes = [] # Clear boxes if not received

    def update_camera_status(self, is_connected):
        """Update title color based on camera status"""
        print("\nCamera Status Update:")
        print("-----------------------")
        if is_connected is None:
            print("Camera status: Initializing")
            self.title.setStyleSheet(f"color: {self.secondary_color};")
            self.camera_feed.setText("Initializing camera...")
        elif is_connected:
            print("Camera status: Connected and validated")
            self.title.setStyleSheet(f"color: {self.success_color};")
            self.camera_feed.setText("Camera connected, waiting for first frame...")
        else:
            print("Camera status: Disconnected or failed validation")
            self.title.setStyleSheet(f"color: {self.secondary_color};")
            self.camera_feed.setText("Camera not available")
        print("-----------------------")

    def update_camera_feed(self, q_image):
        """Update the camera feed display, drawing latest boxes if available."""
        try:
            label_width = self.camera_feed.width()
            label_height = self.camera_feed.height()
            
            if label_width <= 0 or label_height <= 0:
                return # Don't process if label has no size
                
            self._label_size = (label_width, label_height)
            
            if q_image is None or q_image.isNull():
                # print("Received null frame in update_camera_feed") # Debug
                return
                
            # --- Frame Rate Logging --- 
            current_time = time.time()
            if not hasattr(self, '_gui_frame_count'): # Use a different counter name
                self._gui_frame_count = 0
                self._gui_last_fps_time = current_time
            self._gui_frame_count += 1
            if current_time - self._gui_last_fps_time >= 1.0:
                fps = self._gui_frame_count / (current_time - self._gui_last_fps_time)
                print(f"\nGUI Frame Update FPS: {fps:.2f}")
                self._gui_frame_count = 0
                self._gui_last_fps_time = current_time
            
            # --- Scaling --- 
            img_width = q_image.width()
            img_height = q_image.height()
            
            if img_width == 0 or img_height == 0:
                # print("Received frame with zero dimension") # Debug
                return

            # Calculate final display size preserving aspect ratio
            # (This logic determines the size of the pixmap we draw onto)
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

            # Create base pixmap (scaled if necessary)
            pixmap = QPixmap.fromImage(q_image).scaled(
                final_pixmap_width,
                final_pixmap_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # --- Draw Bounding Boxes --- 
            if self.latest_received_boxes: # Check if there are boxes to draw
                 # print(f"Drawing {len(self.latest_received_boxes)} boxes.") # Debug
                 # Calculate scaling factors from original detection res to current pixmap size
                 original_w, original_h = self.detection_resolution
                 scale_x = pixmap.width() / original_w
                 scale_y = pixmap.height() / original_h
                 
                 # Create painter
                 painter = QPainter(pixmap)
                 pen = QPen(Qt.green, 2) # Green pen, 2 pixels wide
                 painter.setPen(pen)
                 painter.setFont(QFont('Arial', 10)) # Font for labels
                 
                 for box_data in self.latest_received_boxes:
                      try:
                          coords = box_data['coords'] # [x1, y1, x2, y2]
                          label = box_data['label']
                          confidence = box_data['conf']
                          
                          # Scale coordinates
                          x1, y1, x2, y2 = [int(c) for c in coords]
                          scaled_x = int(x1 * scale_x)
                          scaled_y = int(y1 * scale_y)
                          scaled_w = int((x2 - x1) * scale_x)
                          scaled_h = int((y2 - y1) * scale_y)
                          
                          # Draw rectangle
                          painter.drawRect(scaled_x, scaled_y, scaled_w, scaled_h)
                          
                          # Draw label WITH confidence above the box
                          label_text = f"{label} ({confidence:.2f})"
                          painter.drawText(scaled_x, scaled_y - 5, label_text)
                          # print(f"Drew box: {label} at {[scaled_x, scaled_y, scaled_w, scaled_h]}") # Debug
                      except KeyError:
                           print(f"Error drawing box: 'conf' key missing in {box_data}")
                      except Exception as draw_e:
                           print(f"Error drawing box {box_data}: {draw_e}")
                 
                 painter.end() # Finish painting
            
            # --- Display Pixmap --- 
            self.camera_feed.setStyleSheet("QLabel { background-color: black; border-radius: 15px; }")
            self.camera_feed.setPixmap(pixmap)
            self.camera_feed.setAlignment(Qt.AlignCenter)
            
            # Clear placeholder text only if it exists
            if self.camera_feed.text():
                # print("Received first valid frame, clearing placeholder text") # Debug
                self.camera_feed.setText("")
                
        except Exception as e:
            print(f"\nError updating camera feed:")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            import traceback
            traceback.print_exc()

    def dispense_item(self, item_key):
        """Dispense an item based on its key"""
        if item_key in self.avend_codes:
            avend_code = self.avend_codes[item_key]
            self.dispense_with_code(avend_code)
        else:
            QMessageBox.warning(self, "Dispense Error", f"No AVend code mapped for {item_key}")
            
    def override_dispense(self):
        """Override function to dispense all items"""
        # Dispense all items in sequence
        for item_key, avend_code in self.avend_codes.items():
            self.dispense_with_code(avend_code)
            
    def dispense_with_code(self, code):
        """Dispense an item with the given AVend code"""
        # Update status to show dispensing
        self.dispensing_status.setText(f"Dispensing {code}...")
        self.dispensing_status.setStyleSheet(f"color: {self.secondary_color};")
        
        # First start a session
        session_response = self.api.start_session()
        
        if not session_response.get("success", False):
            error_msg = session_response.get("error", "Unknown error")
            self.dispensing_status.setText(f"Error: Failed to start session")
            self.dispensing_status.setStyleSheet(f"color: {self.danger_color};")
            return
        
        # Then dispense the item
        dispense_response = self.api.dispense(code=code)
        
        if dispense_response.get("success", False):
            self.dispensing_status.setText(f"Successfully dispensed {code}")
            self.dispensing_status.setStyleSheet(f"color: {self.success_color};")
            
            # Check if this is the first manual dispense
            if not self.first_dispense_done:
                self.first_dispense_done = True
                # Call H1 Service routine after first manual dispense
                self.call_h1_service()
            
            # Reset status after 3 seconds
            QTimer.singleShot(3000, lambda: self.reset_status())
        else:
            error_msg = dispense_response.get("error", "Unknown error")
            self.dispensing_status.setText(f"Error: Failed to dispense {code}")
            self.dispensing_status.setStyleSheet(f"color: {self.danger_color};")
            
    def call_h1_service(self):
        """Start the H1 Service routine that runs every 20 seconds"""
        try:
            # Add a message that we're about to start the service routine
            self.dispensing_status.setText("Starting H1 Service routine...")
            self.dispensing_status.setStyleSheet(f"color: {self.secondary_color};")
            
            # Add a delay before starting the service routine (3 seconds)
            QTimer.singleShot(3000, self._start_h1_service_routine)
            
            print("H1 Service routine will start in 3 seconds")
        except Exception as e:
            print(f"Exception in H1 Service routine setup: {str(e)}")
    
    def _start_h1_service_routine(self):
        """Actually start the H1 Service routine after delay"""
        try:
            # Start the service routine that will call H1 every 20 seconds
            service_response = self.api.start_service_routine()
            
            if service_response.get("success", False):
                print("Successfully started H1 Service routine")
                self.dispensing_status.setText("H1 Service routine started (running every 20s)")
                self.dispensing_status.setStyleSheet(f"color: {self.success_color};")
            else:
                print(f"Error starting H1 Service routine: {service_response.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"Exception in H1 Service routine: {str(e)}")
    
    def reset_status(self):
        """Reset the dispensing status to the default message"""
        self.dispensing_status.setText("Ready to dispense...")
        self.dispensing_status.setStyleSheet("color: #8E8E93;")
        
    def close_application(self):
        """Handle application shutdown"""
        # Stop detection thread
        if hasattr(self, 'detection_thread'):
            self.detection_thread.stop()
            self.detection_thread.wait()
        
        # Close the window
        self.close()
        
        # Exit the application
        QApplication.quit()
        
    def closeEvent(self, event):
        """Handle window close event"""
        # Stop detection thread before closing
        if hasattr(self, 'detection_thread'):
            self.detection_thread.stop()
            self.detection_thread.wait()
            
        # Stop the H1 service routine if it's running
        try:
            if hasattr(self, 'api') and hasattr(self.api, 'stop_service_routine'):
                 # Check if stop_service_routine actually exists if using mock API
                 if callable(self.api.stop_service_routine):
                     self.api.stop_service_routine()
                     print("H1 Service routine stopped")
        except Exception as e:
            print(f"Error stopping H1 Service routine: {str(e)}")
            
        super().closeEvent(event)

    def toggle_help(self):
        """Toggle between main content and help view"""
        if self.is_help_visible:
            self.help_widget.hide()
            self.main_stacked_layout.itemAt(0).widget().show()
            self.help_button.setStyleSheet("""
                QPushButton {
                    background-color: #007AFF;
                    color: white;
                    border-radius: 15px;
                    font-size: 18px;
                    font-weight: bold;
                    border: none;
                    padding: 10px;
                    margin: 2px;
                }
                QPushButton:hover {
                    background-color: #0062CC;
                    padding: 8px;
                    margin: 4px;
                }
                QPushButton:pressed {
                    background-color: #004999;
                    padding: 10px;
                    margin: 2px;
                }
            """)
        else:
            if self.is_settings_visible:
                self.toggle_settings()
            self.main_stacked_layout.itemAt(0).widget().hide()
            self.help_widget.show()
            self.help_button.setStyleSheet("""
                QPushButton {
                    background-color: #34C759;
                    color: white;
                    border-radius: 15px;
                    font-size: 18px;
                    font-weight: bold;
                    border: none;
                    padding: 10px;
                    margin: 2px;
                }
                QPushButton:hover {
                    background-color: #2CB14F;
                    padding: 8px;
                    margin: 4px;
                }
                QPushButton:pressed {
                    background-color: #248F3F;
                    padding: 10px;
                    margin: 2px;
                }
            """)
        self.is_help_visible = not self.is_help_visible

    def toggle_settings(self):
        """Toggle between main content and settings view"""
        if self.is_settings_visible:
            self.settings_widget.hide()
            self.main_stacked_layout.itemAt(0).widget().show()
            self.settings_button.setStyleSheet("""
                QPushButton {
                    background-color: #007AFF;
                    color: white;
                    border-radius: 15px;
                    font-size: 18px;
                    font-weight: bold;
                    border: none;
                    padding: 10px;
                    margin: 2px;
                }
                QPushButton:hover {
                    background-color: #0062CC;
                    padding: 8px;
                    margin: 4px;
                }
                QPushButton:pressed {
                    background-color: #004999;
                    padding: 10px;
                    margin: 2px;
                }
            """)
        else:
            if self.is_help_visible:
                self.toggle_help()
            self.main_stacked_layout.itemAt(0).widget().hide()
            self.settings_widget.show()
            self.settings_button.setStyleSheet("""
                QPushButton {
                    background-color: #34C759;
                    color: white;
                    border-radius: 15px;
                    font-size: 18px;
                    font-weight: bold;
                    border: none;
                    padding: 10px;
                    margin: 2px;
                }
                QPushButton:hover {
                    background-color: #2CB14F;
                    padding: 8px;
                    margin: 4px;
                }
                QPushButton:pressed {
                    background-color: #248F3F;
                    padding: 10px;
                    margin: 2px;
                }
            """)
        self.is_settings_visible = not self.is_settings_visible

    def save_settings(self):
        """Save the AVend settings and reinitialize the API"""
        try:
            host = self.avend_ip_input.text()
            port = int(self.avend_port_input.text())
            self.api = AvendAPI(host=host, port=port)
            self.toggle_settings()  # Return to main view
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid port number!")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save settings: {str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Ensure imports are available
    import cv2
    import torch
    import threading
    import platform
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 