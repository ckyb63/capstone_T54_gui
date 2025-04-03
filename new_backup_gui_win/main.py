import sys
from PySide2.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QGridLayout)
from PySide2.QtCore import Qt, QThread, Signal
from PySide2.QtGui import QFont
from capstone_model import run_detection

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
        self.setFixedSize(600, 800)  # Increased width to 600px
        
        # Create central widget and main layout
        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: white;")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)  # Increase spacing between elements
        main_layout.setContentsMargins(30, 20, 30, 20)  # Increased horizontal margins
        
        # Create header with title and icons
        header_layout = QHBoxLayout()
        header_layout.setSpacing(20)  # Space between header elements
        
        help_button = QPushButton("?")
        help_button.setFixedSize(40, 40)  # Fixed size for circular button
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
        self.title.setFont(QFont('Arial', 24, QFont.Bold))
        self.title.setStyleSheet("color: #FF9500;")  # Initial orange color for "initializing"
        
        settings_button = QPushButton("⚙")
        settings_button.setFixedSize(40, 40)  # Fixed size for circular button
        settings_button.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border-radius: 20px;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        
        close_button = QPushButton("×")
        close_button.setFixedSize(40, 40)  # Fixed size for circular button
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #ff3b30;
                color: white;
                border-radius: 20px;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff453a;
            }
        """)
        close_button.clicked.connect(self.close_application)
        
        header_layout.addWidget(help_button)
        header_layout.addStretch(1)  # Add stretch before title
        header_layout.addWidget(self.title)
        header_layout.addStretch(1)  # Add stretch after title
        header_layout.addWidget(settings_button)
        header_layout.addWidget(close_button)
        
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
        gate_status = QLabel("Gate LOCKED")
        gate_status.setFont(QFont('Arial', 18, QFont.Bold))
        gate_status.setStyleSheet("color: red;")
        gate_status.setAlignment(Qt.AlignCenter)
        
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #e0e0e0;")
        
        dispensing_status = QLabel("Ready to dispense...")
        dispensing_status.setAlignment(Qt.AlignCenter)
        dispensing_status.setFont(QFont('Arial', 16))
        
        status_layout.addWidget(gate_status)
        status_layout.addWidget(separator)
        status_layout.addWidget(dispensing_status)
        
        # Create grid layout for buttons
        button_grid = QGridLayout()
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
            button.setMinimumHeight(80)
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
            button_grid.addWidget(button, row, col)
            self.ppe_buttons[key] = button
        
        # Add all widgets to main layout with proper spacing
        main_layout.addLayout(header_layout)
        main_layout.addSpacing(10)
        main_layout.addWidget(status_card)
        main_layout.addSpacing(20)
        main_layout.addLayout(button_grid)
        main_layout.addStretch()

        # Start detection thread
        self.detection_thread = DetectionThread()
        self.detection_thread.detection_signal.connect(self.update_button_states)
        self.detection_thread.camera_status_signal.connect(self.update_camera_status)
        self.detection_thread.start()

    def update_button_states(self, detection_states):
        """Update button colors based on detection states"""
        for key, detected in detection_states.items():
            if key in self.ppe_buttons:
                button = self.ppe_buttons[key]
                if detected:
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

    def update_camera_status(self, is_connected):
        """Update title color based on camera status"""
        if is_connected:
            self.title.setStyleSheet("color: #4CAF50;")  # Green for connected
        else:
            self.title.setStyleSheet("color: #ff6b6b;")  # Red for disconnected

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
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 