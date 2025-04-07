import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QGridLayout,
                             QLineEdit, QMessageBox)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont

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

    def __init__(self):
        super().__init__()
        self.is_running = True

    def run(self):
        def detection_callback(detection_states):
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
        run_detection(detection_callback)

    def stop(self):
        self.is_running = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PPE Vending Machine")
        self.setFixedSize(500, 650)  # Reduced size to fit laptop displays
        
        # Initialize AVend API with default values
        self.api = AvendAPI()
        self.avend_codes = {
            "hardhat": "A1",
            "glasses": "A2",
            "beardnet": "A3",
            "earplugs": "A4",
            "gloves": "A5"
        }
        
        # Flag to track if first manual dispense has been done
        self.first_dispense_done = False
        
        # Create central widget and main layout
        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: white;")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)  # Increase spacing between elements
        main_layout.setContentsMargins(20, 15, 20, 15)  # Reduced margins
        
        # Create header with title and icons
        header_layout = QHBoxLayout()
        header_layout.setSpacing(20)  # Space between header elements
        
        help_button = QPushButton("?")
        help_button.setFixedSize(35, 35)  # Reduced size for circular button
        help_button.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border-radius: 20px;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        
        # Title that will also serve as camera status
        self.title = QLabel("PPE Vending Machine")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setFont(QFont('Arial', 20, QFont.Bold))  # Reduced font size
        self.title.setStyleSheet("color: #FF9500;")  # Initial orange color for "initializing"
        
        settings_button = QPushButton("⚙")
        settings_button.setFixedSize(35, 35)  # Reduced size for circular button
        settings_button.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border-radius: 20px;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        settings_button.clicked.connect(self.toggle_settings)
        
        header_layout.addWidget(help_button)
        header_layout.addStretch(1)  # Add stretch before title
        header_layout.addWidget(self.title)
        header_layout.addStretch(1)  # Add stretch after title
        header_layout.addWidget(settings_button)
        
        # Create status card
        status_card = QWidget()
        status_card.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
                padding: 20px;
            }
        """)
        status_layout = QVBoxLayout(status_card)
        status_layout.setSpacing(15)
        
        # Status indicators
        self.gate_status = QLabel("Gate LOCKED")
        self.gate_status.setFont(QFont('Arial', 16, QFont.Bold))  # Reduced font size
        self.gate_status.setStyleSheet("color: red;")
        self.gate_status.setAlignment(Qt.AlignCenter)
        
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #e0e0e0;")
        
        self.dispensing_status = QLabel("Ready to dispense...")
        self.dispensing_status.setAlignment(Qt.AlignCenter)
        self.dispensing_status.setFont(QFont('Arial', 14))  # Reduced font size
        
        status_layout.addWidget(self.gate_status)
        status_layout.addWidget(separator)
        status_layout.addWidget(self.dispensing_status)
        
        # Create settings panel (hidden by default)
        self.settings_panel = QWidget()
        self.settings_panel.setVisible(False)  # Hidden by default
        self.settings_panel.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
                padding: 20px;
            }
        """)
        settings_layout = QVBoxLayout(self.settings_panel)
        
        # Settings title
        settings_title = QLabel("Settings")
        settings_title.setFont(QFont('Arial', 16, QFont.Bold))  # Reduced font size
        settings_title.setAlignment(Qt.AlignCenter)
        settings_title.setStyleSheet("color: #333333;")
        
        # IP Configuration
        ip_title = QLabel("AVend API Connection")
        ip_title.setFont(QFont('Arial', 12, QFont.Bold))  # Reduced font size
        ip_title.setStyleSheet("color: #333333; margin-top: 10px;")
        
        # IP form with label and input
        ip_form_widget = QWidget()
        ip_form_layout = QHBoxLayout(ip_form_widget)
        ip_form_layout.setContentsMargins(0, 10, 0, 10)
        
        ip_label = QLabel("IP Address:")
        ip_label.setFont(QFont('Arial', 12))
        ip_label.setStyleSheet("color: #333333;")
        ip_label.setFixedWidth(100)
        
        self.ip_input = QLineEdit("127.0.0.1")
        self.ip_input.setPlaceholderText("Enter AVend IP address")
        self.ip_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
                background-color: white;
                color: #333333;
            }
        """)
        
        self.connect_button = QPushButton("Connect")
        self.connect_button.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0069d9;
            }
        """)
        self.connect_button.clicked.connect(self.connect_to_avend)
        
        ip_form_layout.addWidget(ip_label)
        ip_form_layout.addWidget(self.ip_input, 1)  # Give the input field more space
        ip_form_layout.addWidget(self.connect_button)
        
        # Connection status
        self.connection_status = QLabel("Not connected")
        self.connection_status.setAlignment(Qt.AlignCenter)
        self.connection_status.setStyleSheet("color: #FF9500; font-size: 14px; margin-top: 5px;")
        self.connection_status.setMinimumHeight(30)
        
        # Close settings button
        close_settings_button = QPushButton("Close Settings")
        close_settings_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9500;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #FF8000;
            }
        """)
        close_settings_button.clicked.connect(self.toggle_settings)
        
        # Add all to settings layout
        settings_layout.addWidget(settings_title)
        settings_layout.addSpacing(15)
        settings_layout.addWidget(ip_title)
        settings_layout.addWidget(ip_form_widget)
        settings_layout.addWidget(self.connection_status)
        settings_layout.addStretch()
        settings_layout.addWidget(close_settings_button)
        
        # Create a container for buttons
        self.button_container = QWidget()
        button_grid = QGridLayout(self.button_container)
        button_grid.setSpacing(20)  # Increased spacing between buttons
        
        # Button labels and their positions
        buttons_config = [
            ("Hard Hat", "hardhat", 0, 0),
            ("Safety Glasses", "glasses", 0, 1),
            ("Beard Net", "beardnet", 1, 0),
            ("Ear Plugs", "earplugs", 1, 1),
            ("Gloves", "gloves", 2, 0),
            ("OVERRIDE", "override", 2, 1)
        ]
        
        # Create and style buttons
        self.ppe_buttons = {}
        for label, key, row, col in buttons_config:
            button = QPushButton(label)
            button.setMinimumHeight(60)  # Reduced button height
            if key == "override":
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #FF9500;
                        color: white;
                        border: none;
                        border-radius: 8px;
                        font-size: 14px;
                        font-weight: bold;
                    }
                """)
                button.clicked.connect(self.override_dispense)
            else:
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #ff6b6b;
                        color: white;
                        border: none;
                        border-radius: 8px;
                        font-size: 14px;
                        font-weight: bold;
                    }
                """)
                # Connect each PPE button to its dispense function
                button.clicked.connect(lambda checked, k=key: self.dispense_item(k))
            button_grid.addWidget(button, row, col)
            self.ppe_buttons[key] = button
            
            # Add AVend code label to each button (A1-A5)
            if key in self.avend_codes:
                avend_code = self.avend_codes[key]
                current_text = button.text()
                button.setText(f"{current_text}\n({avend_code})")
        
        # Add all widgets to main layout with proper spacing
        main_layout.addLayout(header_layout)
        main_layout.addSpacing(10)
        main_layout.addWidget(status_card)
        main_layout.addWidget(self.settings_panel)
        main_layout.addSpacing(20)
        main_layout.addWidget(self.button_container)
        main_layout.addStretch()

        # Start detection thread
        self.detection_thread = DetectionThread()
        self.detection_thread.detection_signal.connect(self.update_button_states)
        self.detection_thread.camera_status_signal.connect(self.update_camera_status)
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
                    button.setStyleSheet("""
                        QPushButton {
                            background-color: #4CAF50;
                            color: white;
                            border: none;
                            border-radius: 8px;
                            font-size: 14px;
                            font-weight: bold;
                        }
                    """)
                else:
                    if key == "override":
                        print(f"Setting override button to ORANGE")
                        button.setStyleSheet("""
                            QPushButton {
                                background-color: #FF9500;
                                color: white;
                                border: none;
                                border-radius: 8px;
                                font-size: 14px;
                                font-weight: bold;
                            }
                        """)
                    else:
                        print(f"Setting {key} button to RED (not detected)")
                        button.setStyleSheet("""
                            QPushButton {
                                background-color: #ff6b6b;
                                color: white;
                                border: none;
                                border-radius: 8px;
                                font-size: 14px;
                                font-weight: bold;
                            }
                        """)
            else:
                print(f"Warning: No button found for key {key}")

    def update_camera_status(self, is_connected):
        """Update title color based on camera status"""
        if is_connected:
            self.title.setStyleSheet("color: #4CAF50;")  # Green for connected
        else:
            self.title.setStyleSheet("color: #FF9500;")  # Orange for disconnected
            # We don't use red since the application can still function without a camera

    def toggle_settings(self):
        """Toggle the visibility of the settings panel"""
        # Hide the settings panel if it's visible, show it if it's hidden
        is_visible = self.settings_panel.isVisible()
        self.settings_panel.setVisible(not is_visible)
        
        # Create a container for buttons if not already created
        if not hasattr(self, 'button_container'):
            # Find the button grid layout's parent widget
            for i in range(self.centralWidget().layout().count()):
                item = self.centralWidget().layout().itemAt(i)
                if isinstance(item, QGridLayout):
                    self.button_container = item.parent()
                    break
            else:
                # If we didn't find it, use the last widget before the stretch
                count = self.centralWidget().layout().count()
                if count > 1:
                    self.button_container = self.centralWidget().layout().itemAt(count-2).widget()
        
        # If showing settings, hide the buttons
        if not is_visible:
            self.dispensing_status.setText("Configure AVend API connection...")
            if hasattr(self, 'button_container'):
                self.button_container.setVisible(False)
        else:
            self.reset_status()
            if hasattr(self, 'button_container'):
                self.button_container.setVisible(True)
        
    def connect_to_avend(self):
        """Connect to the AVend API with the specified IP"""
        ip = self.ip_input.text().strip()
        if not ip:
            self.connection_status.setText("Error: Please enter a valid IP address")
            self.connection_status.setStyleSheet("color: #FF3B30;")
            return
            
        try:
            self.api = AvendAPI(host=ip, port=8080)
            self.connection_status.setText(f"Connected to {ip}:8080")
            self.connection_status.setStyleSheet("color: #4CAF50;")
        except Exception as e:
            self.connection_status.setText(f"Error: {str(e)}")
            self.connection_status.setStyleSheet("color: #FF3B30;")
            
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
        self.dispensing_status.setStyleSheet("color: #FF9500;")
        
        # First start a session
        session_response = self.api.start_session()
        
        if not session_response.get("success", False):
            error_msg = session_response.get("error", "Unknown error")
            self.dispensing_status.setText(f"Error: Failed to start session")
            self.dispensing_status.setStyleSheet("color: #FF3B30;")
            return
        
        # Then dispense the item
        dispense_response = self.api.dispense(code=code)
        
        if dispense_response.get("success", False):
            self.dispensing_status.setText(f"Successfully dispensed {code}")
            self.dispensing_status.setStyleSheet("color: #4CAF50;")
            
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
            self.dispensing_status.setStyleSheet("color: #FF3B30;")
            
    def call_h1_service(self):
        """Start the H1 Service routine that runs every 20 seconds"""
        try:
            # Add a message that we're about to start the service routine
            self.dispensing_status.setText("Starting H1 Service routine...")
            self.dispensing_status.setStyleSheet("color: #FF9500;")
            
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
                self.dispensing_status.setStyleSheet("color: #4CAF50;")
            else:
                print(f"Error starting H1 Service routine: {service_response.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"Exception in H1 Service routine: {str(e)}")
    
    def reset_status(self):
        """Reset the dispensing status to the default message"""
        self.dispensing_status.setText("Ready to dispense...")
        self.dispensing_status.setStyleSheet("color: black;")
        
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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 