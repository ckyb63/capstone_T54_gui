# Import all the same dependencies as main.py
import sys
import os
import time
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QGridLayout,
                             QLineEdit, QMessageBox, QFrame, QFormLayout, QTextEdit)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QPalette, QColor, QImage, QPixmap

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

# Try to import the detection model, create a mock if not available
try:
    from capstone_model import run_detection
    HAS_DETECTION_MODEL = True
except ImportError:
    HAS_DETECTION_MODEL = False
    def run_detection(callback):
        print("Mock detection model: No real model available")
        if callback:
            callback(None)

class DetectionThread(QThread):
    detection_signal = Signal(dict)
    camera_status_signal = Signal(bool)
    frame_signal = Signal(QImage)

    def __init__(self):
        super().__init__()
        self.is_running = True

    def run(self):
        def detection_callback(detection_states, frame=None):
            if detection_states is None:
                self.camera_status_signal.emit(False)
                if not HAS_DETECTION_MODEL:
                    mock_states = {
                        "hardhat": True,
                        "glasses": True,
                        "beardnet": True,
                        "earplugs": True,
                        "gloves": True
                    }
                    self.detection_signal.emit(mock_states)
            else:
                self.camera_status_signal.emit(True)
                self.detection_signal.emit(detection_states)
                
                if frame is not None:
                    height, width, channel = frame.shape
                    bytes_per_line = 3 * width
                    q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
                    self.frame_signal.emit(q_image)

        run_detection(detection_callback)

    def stop(self):
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
        # Calculate size based on button dimensions plus spacing
        camera_width = 2 * 180 + 20  # 2 buttons wide + spacing
        camera_height = 2 * 120 + 20  # 2 buttons high + spacing
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
        content_layout.addWidget(self.camera_feed, 2)  # 2/3 width
        
        # Create a container for the button grid
        button_container = QWidget()
        button_container_layout = QVBoxLayout(button_container)
        button_container_layout.addStretch(1)
        button_container_layout.addLayout(button_grid)
        button_container_layout.addStretch(1)
        content_layout.addWidget(button_container, 1)  # 1/3 width

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
        self.detection_thread.detection_signal.connect(self.update_button_states)
        self.detection_thread.camera_status_signal.connect(self.update_camera_status)
        self.detection_thread.frame_signal.connect(self.update_camera_feed)
        self.detection_thread.start()

        # Flag to track if first manual dispense has been done
        self.first_dispense_done = False

    def update_button_states(self, detection_states):
        """Update button colors based on detection states"""
        print(f"Received detection states: {detection_states}")
        for key, detected in detection_states.items():
            print(f"Processing key: {key}, detected: {detected}")
            if key in self.ppe_buttons:
                button = self.ppe_buttons[key]
                print(f"Found button for {key}: {button.text()}")
                if detected:
                    print(f"Setting {key} button to GREEN (detected)")
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
                else:
                    if key == "override":
                        print(f"Setting override button to ORANGE")
                        button.setStyleSheet(f"""
                            QPushButton {{
                                background-color: {self.secondary_color};
                                color: white;
                                border-radius: 12px;
                                font-size: 20px;
                                font-weight: bold;
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
                        print(f"Setting {key} button to RED (not detected)")
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
                print(f"Warning: No button found for key {key}")

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
        """Update the camera feed display with the latest frame"""
        try:
            # Cache the label size to avoid repeated calculations
            if not hasattr(self, '_label_size'):
                self._label_size = (self.camera_feed.width(), self.camera_feed.height())
                print(f"\nInitialized camera feed display size: {self._label_size}")
                print("Waiting for first frame...")
            
            if q_image is None:
                if not hasattr(self, '_null_frame_count'):
                    self._null_frame_count = 0
                self._null_frame_count += 1
                
                if self._null_frame_count % 10 == 0:  # Only print every 10th null frame
                    print(f"\nReceived null frame (count: {self._null_frame_count})")
                return
                
            # Reset null frame counter when we get a valid frame
            if hasattr(self, '_null_frame_count'):
                self._null_frame_count = 0
            
            # Track frame statistics
            if not hasattr(self, '_frame_count'):
                self._frame_count = 0
                self._last_fps_time = time.time()
                self._last_frame_time = time.time()
            
            self._frame_count += 1
            current_time = time.time()
            
            # Calculate and print FPS every second
            if current_time - self._last_fps_time >= 1.0:
                fps = self._frame_count / (current_time - self._last_fps_time)
                frame_interval = (current_time - self._last_fps_time) / self._frame_count
                print(f"\nGUI Frame Stats:")
                print(f"FPS: {fps:.2f}")
                print(f"Frame interval: {frame_interval*1000:.1f}ms")
                print(f"Frame size: {q_image.width()}x{q_image.height()}")
                self._frame_count = 0
                self._last_fps_time = current_time
            
            self._last_frame_time = current_time
            
            # Calculate scaling while preserving aspect ratio
            src_aspect = q_image.width() / q_image.height()
            dst_aspect = self._label_size[0] / self._label_size[1]
            
            if src_aspect > dst_aspect:
                # Image is wider than display area
                new_width = self._label_size[0]
                new_height = int(new_width / src_aspect)
            else:
                # Image is taller than display area
                new_height = self._label_size[1]
                new_width = int(new_height * src_aspect)
            
            # Only scale if needed and use high-quality scaling
            if q_image.width() != new_width or q_image.height() != new_height:
                scaled_pixmap = QPixmap.fromImage(q_image).scaled(
                    new_width,
                    new_height,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            else:
                scaled_pixmap = QPixmap.fromImage(q_image)
            
            # Center the image in the label
            x_offset = max(0, (self._label_size[0] - new_width) // 2)
            y_offset = max(0, (self._label_size[1] - new_height) // 2)
            
            # Clear the label and set style for black background
            self.camera_feed.setStyleSheet("QLabel { background-color: black; }")
            
            # Set the pixmap with proper alignment
            self.camera_feed.setPixmap(scaled_pixmap)
            self.camera_feed.setAlignment(Qt.AlignCenter)
            
            # Clear placeholder text only on first frame
            if self.camera_feed.text():
                print("\nReceived first valid frame, clearing placeholder text")
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
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 