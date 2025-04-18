import sys
import os
import time
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QGridLayout,
                             QLineEdit, QMessageBox, QFrame, QFormLayout)
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
    # Create a mock function
    def run_detection(callback):
        print("Mock detection model: No real model available")
        # Call the callback with None to indicate camera is not available
        if callback:
            callback(None)

class DetectionThread(QThread):
    detection_signal = Signal(dict)  # Signal to send detection results
    camera_status_signal = Signal(bool)  # Signal to send camera status
    frame_signal = Signal(QImage)  # Signal to send camera frames

    def __init__(self):
        super().__init__()
        self.is_running = True

    def run(self):
        def detection_callback(detection_states, frame=None):
            if detection_states is None:
                self.camera_status_signal.emit(False)
                # If no camera, create mock detection states where all items are detected
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
                
                # Convert frame to QImage and emit if available
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
        self.setFixedSize(600, 800)
        
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
        self.primary_color = "#FF7B7B"  # Coral pink for PPE buttons
        self.secondary_color = "#FFA500"  # Orange for override
        self.success_color = "#34C759"  # Green
        self.danger_color = "#FF3B30"  # Red
        
        # Set window style to be more classic/retro
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        
        # Central widget and main layout
        central_widget = QWidget()
        central_widget.setStyleSheet("""
            QWidget {
                background-color: #F0F0F0;
            }
        """)
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header with title and buttons
        header_layout = QHBoxLayout()
        
        # Help button
        self.help_button = QPushButton("?")
        self.help_button.setFixedSize(50, 50)
        self.help_button.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border-radius: 25px;
                font-size: 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0062CC;
            }
        """)
        
        # Title
        self.title = QLabel("PPE Vending Machine")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setFont(QFont('Arial', 24, QFont.Bold))
        self.title.setStyleSheet("color: black;")
        
        # Settings button
        self.settings_button = QPushButton("⚙")
        self.settings_button.setFixedSize(50, 50)
        self.settings_button.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border-radius: 25px;
                font-size: 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0062CC;
            }
        """)
        self.settings_button.clicked.connect(self.toggle_settings)
        
        header_layout.addWidget(self.help_button)
        header_layout.addStretch(1)
        header_layout.addWidget(self.title)
        header_layout.addStretch(1)
        header_layout.addWidget(self.settings_button)
        
        # Status section
        status_layout = QHBoxLayout()
        
        # Gate status
        self.gate_status = QLabel("Gate LOCKED")
        self.gate_status.setFont(QFont('Arial', 16, QFont.Bold))
        self.gate_status.setStyleSheet(f"color: {self.danger_color};")
        
        # Dispensing status
        self.dispensing_status = QLabel("Ready to dispense...")
        self.dispensing_status.setFont(QFont('Arial', 16))
        self.dispensing_status.setStyleSheet("color: black;")
        
        status_layout.addWidget(self.gate_status)
        status_layout.addStretch(1)
        status_layout.addWidget(self.dispensing_status)
        
        # Camera feed placeholder
        self.camera_feed = QLabel()
        self.camera_feed.setFixedHeight(400)
        self.camera_feed.setStyleSheet("""
            QLabel {
                border: 2px dashed #999;
                background-color: white;
                border-radius: 10px;
            }
        """)
        self.camera_feed.setAlignment(Qt.AlignCenter)
        self.camera_feed.setText("Camera Feed Placeholder")
        
        # Button grid
        button_grid = QGridLayout()
        button_grid.setSpacing(15)
        
        # Configure buttons
        buttons_config = [
            ("Hard Hat", "hardhat", 0, 0),
            ("Beard Net", "beardnet", 0, 1),
            ("Gloves", "gloves", 0, 2),
            ("Safety Glasses", "glasses", 1, 0),
            ("Ear Plugs", "earplugs", 1, 1),
            ("OVERRIDE", "override", 1, 2)
        ]
        
        self.ppe_buttons = {}
        for label, key, row, col in buttons_config:
            button = QPushButton(label)
            button.setFixedSize(180, 80)
            
            if key == "override":
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {self.secondary_color};
                        color: white;
                        border-radius: 10px;
                        font-size: 16px;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background-color: #E59400;
                    }}
                """)
                button.clicked.connect(self.override_dispense)
            else:
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {self.primary_color};
                        color: white;
                        border-radius: 10px;
                        font-size: 16px;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background-color: #FF6B6B;
                    }}
                """)
                button.clicked.connect(lambda checked, k=key: self.dispense_item(k))
            
            button_grid.addWidget(button, row, col)
            self.ppe_buttons[key] = button
        
        # Add all widgets to main layout
        main_layout.addLayout(header_layout)
        main_layout.addLayout(status_layout)
        main_layout.addWidget(self.camera_feed)
        main_layout.addLayout(button_grid)
        main_layout.addStretch()

        # Flag to track if first manual dispense has been done
        self.first_dispense_done = False
        
        # Start detection thread
        self.detection_thread = DetectionThread()
        self.detection_thread.detection_signal.connect(self.update_button_states)
        self.detection_thread.camera_status_signal.connect(self.update_camera_status)
        self.detection_thread.frame_signal.connect(self.update_camera_feed)
        self.detection_thread.start()

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
                            border-radius: 10px;
                            font-size: 14px;
                            font-weight: bold;
                        }}
                    """)
                else:
                    if key == "override":
                        print(f"Setting override button to ORANGE")
                        button.setStyleSheet(f"""
                            QPushButton {{
                                background-color: {self.secondary_color};
                                color: white;
                                border-radius: 10px;
                                font-size: 14px;
                                font-weight: bold;
                            }}
                            QPushButton:hover {{
                                background-color: #E59400;
                            }}
                        """)
                    else:
                        print(f"Setting {key} button to RED (not detected)")
                        button.setStyleSheet(f"""
                            QPushButton {{
                                background-color: {self.danger_color};
                                color: white;
                                border-radius: 10px;
                                font-size: 14px;
                                font-weight: bold;
                            }}
                            QPushButton:hover {{
                                background-color: #CC2A25;
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

    def toggle_settings(self):
        """Toggle the visibility of the settings panel"""
        if not hasattr(self, 'settings_panel'):
            # Create settings panel if it doesn't exist
            self.create_settings_panel()
        
        # Toggle visibility
        is_visible = self.settings_panel.isVisible()
        self.settings_panel.setVisible(not is_visible)
        
        # Update UI based on visibility
        if not is_visible:
            # Hide all main elements
            self.dispensing_status.setVisible(False)
            self.gate_status.setVisible(False)
            self.button_container.setVisible(False)
            self.camera_feed.setVisible(False)
            self.title.setVisible(False)
            self.settings_button.setVisible(False)
            self.help_button.setVisible(False)
            
            # Show settings panel
            self.settings_panel.setVisible(True)
        else:
            # Show all main elements
            self.dispensing_status.setVisible(True)
            self.gate_status.setVisible(True)
            self.button_container.setVisible(True)
            self.camera_feed.setVisible(True)
            self.title.setVisible(True)
            self.settings_button.setVisible(True)
            self.help_button.setVisible(True)
            
            # Hide settings panel
            self.settings_panel.setVisible(False)
            self.reset_status()

    def create_settings_panel(self):
        """Create the settings panel with IP configuration"""
        self.settings_panel = QWidget()
        self.settings_panel.setVisible(False)
        self.settings_panel.setStyleSheet("""
            QWidget {
                background-color: white;
            }
            QLabel {
                color: #333333;
                font-size: 14px;
            }
            QLineEdit {
                border: 1px solid #D1D1D6;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
                min-height: 20px;
                background-color: white;
                color: #000000;
            }
        """)

        settings_layout = QVBoxLayout(self.settings_panel)
        settings_layout.setSpacing(15)
        settings_layout.setContentsMargins(20, 20, 20, 20)

        # Title with green text
        title = QLabel("PPE Vending Machine")
        title.setFont(QFont('Arial', 24))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2ECC71; margin-bottom: 10px;")

        # Settings subtitle
        settings_title = QLabel("API Configuration")
        settings_title.setFont(QFont('Arial', 16))
        settings_title.setAlignment(Qt.AlignCenter)
        settings_title.setStyleSheet("color: #FF7B7B; margin: 10px 0;")

        # Form container with white background
        form_container = QWidget()
        form_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 8px;
            }
        """)
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(10)
        form_layout.setContentsMargins(15, 15, 15, 15)

        # IP and Port inputs in horizontal layout
        input_layout = QHBoxLayout()
        
        # IP input
        ip_container = QVBoxLayout()
        ip_label = QLabel("IP:")
        self.ip_input = QLineEdit("127.0.0.1")
        self.ip_input.setFixedWidth(200)
        ip_container.addWidget(ip_label)
        ip_container.addWidget(self.ip_input)
        
        # Port input
        port_container = QVBoxLayout()
        port_label = QLabel("Port:")
        self.port_input = QLineEdit("8080")
        self.port_input.setFixedWidth(80)
        port_container.addWidget(port_label)
        port_container.addWidget(self.port_input)
        
        input_layout.addLayout(ip_container)
        input_layout.addLayout(port_container)
        input_layout.addStretch()
        
        # Add inputs to form
        form_layout.addLayout(input_layout)

        # Connection status
        self.connection_status = QLabel("Not connected")
        self.connection_status.setAlignment(Qt.AlignCenter)
        self.connection_status.setStyleSheet("""
            font-size: 14px;
            color: #8E8E93;
            margin: 10px 0;
        """)
        form_layout.addWidget(self.connection_status)

        # Close button
        close_button = QPushButton("Close")
        close_button.setFixedHeight(40)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #FFA500;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FF9400;
            }
        """)
        close_button.clicked.connect(self.toggle_settings)

        # Add all components to main layout
        settings_layout.addWidget(title)
        settings_layout.addWidget(settings_title)
        settings_layout.addWidget(form_container)
        settings_layout.addStretch()
        settings_layout.addWidget(close_button)

        # Add settings panel to main layout, replacing the camera feed
        self.centralWidget().layout().insertWidget(2, self.settings_panel)

    def connect_to_avend(self):
        """Connect to the AVend API with the specified IP and port"""
        ip = self.ip_input.text().strip()
        port = self.port_input.text().strip()
        
        if not ip or not port:
            self.connection_status.setText("Error: Please enter valid IP and port")
            self.connection_status.setStyleSheet(f"color: {self.danger_color};")
            return
            
        try:
            print(f"\nAttempting to connect to AVend API at {ip}:{port}")
            self.api = AvendAPI(host=ip, port=int(port))
            
            # Test connection with a session start
            response = self.api.start_session()
            if response.get("success", False):
                self.connection_status.setText(f"Connected to {ip}:{port}")
                self.connection_status.setStyleSheet(f"color: {self.success_color};")
                print("Successfully connected to AVend API")
            else:
                error_msg = response.get("error", "Unknown error")
                self.connection_status.setText(f"Connection test failed: {error_msg}")
                self.connection_status.setStyleSheet(f"color: {self.danger_color};")
                print(f"Connection test failed: {error_msg}")
                
        except Exception as e:
            self.connection_status.setText(f"Error: {str(e)}")
            self.connection_status.setStyleSheet(f"color: {self.danger_color};")
            print(f"Error connecting to AVend API: {str(e)}")
            
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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 