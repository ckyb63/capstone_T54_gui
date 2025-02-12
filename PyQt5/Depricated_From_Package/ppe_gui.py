#!/usr/bin/env python3
"""
Stable PPE Vending Machine GUI Node
--------------------------------------
A resizable version of the PPE Vending Machine GUI that adapts layout based on window orientation.
Integrates with ROS2 for real-time PPE detection status and vending control.

Author: Max Chen
Version: 0.2.0
"""

import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QWidget, 
                            QGridLayout, QLabel, QVBoxLayout, QHBoxLayout,
                            QMessageBox, QDialog)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool
import threading
import time
import os
import signal
from contextlib import contextmanager

@contextmanager
def ros_context():
    """Context manager for ROS initialization and shutdown"""
    try:
        rclpy.init()
        yield
    finally:
        try:
            rclpy.shutdown()
        except Exception:
            pass

class ROSNode(Node):
    def __init__(self):
        super().__init__('ppe_gui_node')
        
        # Create subscriber for PPE status
        self.subscription = self.create_subscription(
            String,
            'ppe_status',
            self.ppe_status_callback,
            10)
        
        # Create publisher for dispense requests
        self.dispense_publisher = self.create_publisher(
            String,
            'pleaseDispense',
            10)
            
        # Create publisher for gate status
        self.gate_publisher = self.create_publisher(
            Bool,
            'gate',
            10)
        
        # Reference to GUI (will be set later)
        self.gui = None
        
        self.get_logger().info('ROS Node initialized')

    def ppe_status_callback(self, msg):
        """Handle incoming PPE status messages"""
        if self.gui and not self.gui.is_shutting_down:
            # Use signal to update GUI
            self.gui.status_update_signal.emit(msg.data)
            self.get_logger().info(f'Received PPE status: {msg.data}')

    def publish_dispense_request(self, ppe_name):
        """Publish a request to dispense a PPE item"""
        msg = String()
        msg.data = ppe_name
        self.dispense_publisher.publish(msg)
        self.get_logger().info(f'Published dispense request for: {ppe_name}')

    def publish_gate_status(self, is_locked):
        """Publish safety gate status"""
        msg = Bool()
        msg.data = is_locked
        self.gate_publisher.publish(msg)
        self.get_logger().info(f'Published gate status: {"locked" if is_locked else "unlocked"}')

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("PPE Vending Machine Help")
        self.setModal(True)  # Make dialog modal
        
        # Create main layout
        layout = QVBoxLayout(self)
        
        # Help text
        help_text = """
<h1>PPE Vending Machine Help</h1>

<h2>Operation:</h2>
<ul style='font-size: 14pt;'>
<li>The system detects required PPE items</li>
<li>Green buttons indicate detected PPE</li>
<li>Red buttons indicate missing PPE</li>
<li>The user may need to rotate head to fully detect all requiredPPE</li>
</ul>

<h2>Dispensing:</h2>
<ul style='font-size: 14pt;'>
<li>Click any PPE button to dispense that item</li>
<li>There is a 1 second cooldown between dispense requests</li>
<li>The safety gate remains locked until all required PPE is detected</li>
</ul>

<h2>Safety Override:</h2>
<ul style='font-size: 14pt;'>
<li>Orange OVERRIDE button for emergency or administrative override only</li>
<li>Override unlocks the gate for 10 seconds</li>
</ul>
"""
        text_label = QLabel(help_text)
        text_label.setTextFormat(Qt.RichText)
        layout.addWidget(text_label)
        
        # Add accessibility toggle
        toggle_container = QWidget()
        toggle_layout = QHBoxLayout(toggle_container)
        
        toggle_label = QLabel("Accessibility Mode (O/X Indicators):")
        toggle_label.setFont(QFont('Arial', 12))
        toggle_layout.addWidget(toggle_label)
        
        self.toggle_button = QPushButton("OFF" if not parent.accessibility_mode else "ON")
        self.toggle_button.setFont(QFont('Arial', 12, QFont.Bold))
        self.toggle_button.setFixedSize(100, 40)
        self.toggle_button.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        self.toggle_button.clicked.connect(self.toggle_accessibility)
        toggle_layout.addWidget(self.toggle_button)
        
        layout.addWidget(toggle_container)
        
        # Add OK button
        button_box = QWidget()
        button_layout = QHBoxLayout(button_box)
        ok_button = QPushButton("OK")
        ok_button.setFont(QFont('Arial', 12))
        ok_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        layout.addWidget(button_box)
        
        # Set dialog styling
        self.setStyleSheet("""
            QDialog {
                min-width: 600px;
            }
            QLabel {
                font-size: 14pt;
            }
            QPushButton {
                font-size: 12pt;
                padding: 5px 10px;
            }
        """)
        
    def toggle_accessibility(self):
        """Toggle accessibility mode"""
        self.parent.accessibility_mode = not self.parent.accessibility_mode
        self.toggle_button.setText("ON" if self.parent.accessibility_mode else "OFF")
        self.toggle_button.setStyleSheet("""
            QPushButton {
                background-color: %s;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: %s;
            }
        """ % (('#4caf50' if self.parent.accessibility_mode else '#666'),
               ('#45a049' if self.parent.accessibility_mode else '#555')))
        self.parent.update_status_displays()

class ExperimentalPPEVendingMachine(QMainWindow):
    # Add signals for thread-safe updates
    shutdown_signal = pyqtSignal()
    status_update_signal = pyqtSignal(str)
    gate_status_signal = pyqtSignal(bool)
    
    def __init__(self, ros_node):
        super().__init__()
        self.ros_node = ros_node
        
        # Add accessibility setting
        self.accessibility_mode = False
        
        # Connect signals to slots
        self.status_update_signal.connect(self.handle_status_update)
        self.gate_status_signal.connect(self.handle_gate_status)
        
        # Initialize PPE status
        self.ppe_status = {
            'hardhat': False,
            'beardnet': False,
            'gloves': False,
            'glasses': False,
            'earplugs': False
        }
        self.safety_gate_locked = True
        
        # Cooldown tracking
        self.last_dispense_time = 0
        self.dispense_cooldown = 1.0  # 1 second cooldown
        
        # Initialize shutdown flag
        self.is_shutting_down = False
        
        # Create main widget and layouts
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        
        # Create both portrait and landscape layouts
        self.portrait_layout = QVBoxLayout()
        self.landscape_layout = QHBoxLayout()
        
        # Main layout that will switch between portrait and landscape
        self.main_layout = QVBoxLayout(self.main_widget)
        
        # Initialize resize timer first
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.handleResize)
        
        # Initialize UI first
        self.initUI()
        self.setupLayouts()
        
        # Now initialize other timers after UI elements exist
        # Override reset timer
        self.override_timer = QTimer()
        self.override_timer.timeout.connect(self.reset_override)
        self.override_timer.setSingleShot(True)
        self.override_duration = 10.0  # 10 seconds override duration
        
        # Override countdown timer
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_timer.setInterval(1000)  # Update every second
        self.time_remaining = self.override_duration
        
        # Update timer for status
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status_displays)
        self.timer.start(100)  # Update every 100ms
        
        # Status message timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.reset_status)
        self.status_timer.setSingleShot(True)

    def initUI(self):
        """Initialize UI elements"""
        # Create all widgets
        self.createTitleSection()
        self.createStatusSection()
        self.createCameraSection()
        self.createPPEGrid()
        
        # Window setup
        self.setWindowTitle('Experimental PPE Vending Machine')
        self.setMinimumSize(650, 900)  # Set minimum size same as starting size
        self.resize(650, 900)  # Set initial window size

    def createTitleSection(self):
        """Create title and status section"""
        self.title_widget = QWidget()
        title_layout = QVBoxLayout(self.title_widget)
        
        # Create header with title and help button
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        
        # Help button (left)
        help_button = QPushButton("?")
        help_button.setFont(QFont('Arial', 16, QFont.Bold))
        help_button.setFixedSize(40, 40)
        help_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border-radius: 20px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        help_button.clicked.connect(self.show_help)
        header_layout.addWidget(help_button)
        
        # Title (centered)
        title = QLabel('PPE Vending Machine')
        title.setFont(QFont('Arial', 24))
        title.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title)
        
        # Add empty widget for spacing
        spacer = QWidget()
        spacer.setFixedSize(40, 40)
        header_layout.addWidget(spacer)
        
        title_layout.addWidget(header_widget)
        
        # Status line widget (contains both gate status and status message)
        status_line = QWidget()
        status_layout = QHBoxLayout(status_line)
        
        # Gate status
        self.gate_status = QLabel('Gate LOCKED')
        self.gate_status.setFont(QFont('Arial', 20, QFont.Bold))
        self.gate_status.setStyleSheet("""
            QLabel {
                color: red;
                font-weight: bold;
                padding: 5px;
            }
        """)
        status_layout.addWidget(self.gate_status)
        
        # Add stretch to push gate status and status label apart
        status_layout.addStretch(1)
        
        # Status message
        self.status_label = QLabel('Ready to dispense...')  # Removed "Status: " prefix
        self.status_label.setFont(QFont('Arial', 18, QFont.Bold))
        self.status_label.setStyleSheet('color: black;')
        status_layout.addWidget(self.status_label)
        
        title_layout.addWidget(status_line)

    def createStatusSection(self):
        """Create status section"""
        self.status_widget = QWidget()
        status_layout = QVBoxLayout(self.status_widget)
        # Empty widget to maintain layout structure
        status_layout.addStretch()

    def createCameraSection(self):
        """Create camera feed section"""
        self.camera_widget = QWidget()
        camera_layout = QVBoxLayout(self.camera_widget)
        
        # Camera feed placeholder
        self.camera_placeholder = QLabel('Camera Feed Placeholder')
        self.camera_placeholder.setStyleSheet("""
            QLabel {
                border: 2px dashed #666;
                background: #f0f0f0;
                min-height: 400px;  /* Minimum height to maintain visibility */
                padding: 10px;
            }
        """)
        self.camera_placeholder.setFont(QFont('Arial', 14))  # Make placeholder text more visible
        self.camera_placeholder.setAlignment(Qt.AlignCenter)
        camera_layout.addWidget(self.camera_placeholder)

    def createPPEGrid(self):
        """Create PPE buttons grid"""
        self.ppe_buttons = {}
        self.ppe_indicators = {}  # Add storage for indicators
        
        ppe_items = [
            ('Hard Hat', 'hardhat'),
            ('Beard Net', 'beardnet'),
            ('Gloves', 'gloves'),
            ('Safety Glasses', 'glasses'),
            ('Ear Plugs', 'earplugs'),
            ('OVERRIDE', 'override')
        ]
        
        for label, key in ppe_items:
            # Create container for button and indicator
            container = QWidget()
            layout = QHBoxLayout(container)
            
            # Create button
            button = QPushButton(label)
            button.setFont(QFont('Arial', 12, QFont.Bold))
            button.setMinimumHeight(60)
            button.setStyleSheet("""
                QPushButton {
                    background-color: #ff6b6b;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #ff5252;
                }
                QPushButton:pressed {
                    background-color: #ff3838;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                }
            """)
            button.clicked.connect(lambda checked, k=key: self.on_ppe_button_click(k))
            self.ppe_buttons[key] = button
            
            # Create indicator label (hidden by default)
            indicator = QLabel('')
            indicator.setFont(QFont('Arial', 16, QFont.Bold))
            indicator.setFixedWidth(30)
            indicator.setAlignment(Qt.AlignCenter)
            indicator.hide()
            self.ppe_indicators[key] = indicator
            
            # Add to layout
            layout.addWidget(button)
            layout.addWidget(indicator)
            
            self.ppe_buttons[key] = container

    def setupLayouts(self):
        """Set up portrait and landscape layouts"""
        # Create container widgets
        self.portrait_widget = QWidget()
        self.landscape_widget = QWidget()
        
        # Portrait layout (exactly like ppe_gui)
        portrait_layout = QVBoxLayout(self.portrait_widget)
        
        # Add pre-created widgets
        portrait_layout.addWidget(self.title_widget)
        portrait_layout.addWidget(self.camera_widget)
        portrait_layout.addWidget(self.status_widget)
        
        # PPE Buttons Grid for portrait (2x3)
        portrait_grid = QWidget()
        grid = QGridLayout(portrait_grid)
        
        # Portrait grid positions (2x3)
        portrait_positions = [
            ('hardhat', 0, 0), ('beardnet', 0, 1), ('gloves', 0, 2),
            ('glasses', 1, 0), ('earplugs', 1, 1), ('override', 1, 2)
        ]
        
        for key, row, col in portrait_positions:
            grid.addWidget(self.ppe_buttons[key], row, col)
        
        portrait_layout.addWidget(portrait_grid)
        
        # Landscape layout
        landscape_layout = QHBoxLayout(self.landscape_widget)
        
        # Left panel
        left_widget = QWidget()
        left_panel = QVBoxLayout(left_widget)
        
        # Add pre-created widgets to left panel
        left_panel.addWidget(self.title_widget)
        left_panel.addWidget(self.status_widget)
        
        # Buttons in single column for landscape mode
        button_widget = QWidget()
        button_layout = QVBoxLayout(button_widget)
        button_layout.setSpacing(20)  # Increase spacing between buttons
        
        # Add stretch at the top
        button_layout.addStretch(1)
        
        # Landscape button order (single column)
        landscape_order = ['hardhat', 'beardnet', 'gloves', 'glasses', 'earplugs', 'override']
        
        for key in landscape_order:
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.addWidget(self.ppe_buttons[key], stretch=4)
            button_layout.addWidget(container)
            
            # Add spacing after each button except the last one
            if key != 'override':
                button_layout.addSpacing(10)
        
        # Add stretch at the bottom
        button_layout.addStretch(1)
        
        left_panel.addWidget(button_widget)
        left_panel.addStretch()
        
        # Right panel (camera)
        right_widget = QWidget()
        right_panel = QVBoxLayout(right_widget)
        right_panel.addWidget(self.camera_widget)
        
        # Add panels to landscape layout
        landscape_layout.addWidget(left_widget, 2)
        landscape_layout.addWidget(right_widget, 3)
        
        # Start with portrait layout
        self.main_layout.addWidget(self.portrait_widget)
        self.landscape_widget.hide()
        
        # Show the window
        self.show()

    def resizeEvent(self, event):
        """Handle window resize events"""
        super().resizeEvent(event)
        # Use timer to prevent too frequent updates
        self.resize_timer.start(100)

    def handleResize(self):
        """Update layout based on window size"""
        self.updateLayout()

    def updateLayout(self):
        """Switch between portrait and landscape layouts"""
        size = self.size()
        is_landscape = size.width() > size.height()
        
        # Remove current widget from main layout
        if self.main_layout.count():
            self.main_layout.takeAt(0)
        
        # Reparent widgets before switching layouts
        self.title_widget.setParent(None)
        self.camera_widget.setParent(None)
        self.status_widget.setParent(None)
        
        # Get all button containers
        button_containers = []
        for key in self.ppe_buttons:
            button = self.ppe_buttons[key]
            button.setParent(None)
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.addWidget(button, stretch=4)
            button_containers.append((key, container))
        
        if is_landscape:
            # Setup landscape layout
            landscape = QWidget()
            landscape_layout = QHBoxLayout(landscape)
            
            # Left panel (controls)
            left_widget = QWidget()
            left_layout = QVBoxLayout(left_widget)
            left_layout.setSpacing(20)
            
            # Add top stretch for vertical centering
            left_layout.addStretch(1)
            
            # Title and status at the top
            left_layout.addWidget(self.title_widget)
            left_layout.addWidget(self.status_widget)
            
            # Buttons in single column
            button_widget = QWidget()
            button_layout = QVBoxLayout(button_widget)
            button_layout.setSpacing(20)
            
            # Add buttons
            for key, container in button_containers:
                button_layout.addWidget(container)
                if key != 'override':
                    button_layout.addSpacing(10)
            
            left_layout.addWidget(button_widget)
            
            # Add bottom stretch for vertical centering
            left_layout.addStretch(1)
            
            # Right panel (camera)
            right_widget = QWidget()
            right_layout = QVBoxLayout(right_widget)
            right_layout.addStretch(1)
            right_layout.addWidget(self.camera_widget, 1)  # Allow camera to expand
            right_layout.addStretch(1)
            
            # Add panels to landscape layout with proper proportions
            landscape_layout.addWidget(left_widget, 2)  # Take 2 parts
            landscape_layout.addWidget(right_widget, 3)  # Take 3 parts
            
            self.main_layout.addWidget(landscape)
            
        else:
            # Setup portrait layout
            portrait = QWidget()
            layout = QVBoxLayout(portrait)
            layout.setSpacing(10)  # Reduce spacing between widgets
            
            # Add widgets in portrait order
            layout.addWidget(self.title_widget)
            layout.addWidget(self.camera_widget, 1)  # Add stretch factor
            layout.addWidget(self.status_widget)
            
            # Create 2x3 grid for buttons
            grid_widget = QWidget()
            grid = QGridLayout(grid_widget)
            grid.setSpacing(10)  # Reduce spacing between buttons
            positions = [
                ('hardhat', 0, 0), ('beardnet', 0, 1), ('gloves', 0, 2),
                ('glasses', 1, 0), ('earplugs', 1, 1), ('override', 1, 2)
            ]
            
            for key, row, col in positions:
                for button_key, container in button_containers:
                    if key == button_key:
                        grid.addWidget(container, row, col)
                        break
            
            layout.addWidget(grid_widget)
            layout.setStretchFactor(grid_widget, 0)  # Don't stretch the grid
            
            # Set margins
            layout.setContentsMargins(10, 10, 10, 10)
            grid.setContentsMargins(0, 0, 0, 0)
            
            self.main_layout.addWidget(portrait)
        
        # Force layout update
        self.main_layout.update()
        QApplication.processEvents()

    def confirm_override(self):
        """Show confirmation dialog for override"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("Are you sure you want to override the safety system?")
        msg.setInformativeText("This will unlock the safety gate for 10 seconds.")
        msg.setWindowTitle("Confirm Override")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        
        return msg.exec_() == QMessageBox.Yes

    def on_ppe_button_click(self, ppe_name):
        """Handle PPE button clicks"""
        current_time = time.time()
        
        if ppe_name == 'override':
            if not self.confirm_override():
                return
                
            for ppe in self.ppe_status:
                self.ppe_status[ppe] = True
            self.safety_gate_locked = False
            
            self.ros_node.publish_dispense_request('OVERRIDE')
            self.ros_node.publish_gate_status(self.safety_gate_locked)
            
            self.ppe_buttons['override'].setEnabled(False)
            self.override_timer.start(int(self.override_duration * 1000))
            
            self.time_remaining = self.override_duration
            self.update_countdown()
            self.countdown_timer.start()
            
            self.show_status(f"Override activated for {int(self.override_duration)}s!", "green")
            
        else:
            if current_time - self.last_dispense_time < self.dispense_cooldown:
                remaining = round(self.dispense_cooldown - (current_time - self.last_dispense_time), 1)
                self.show_status(f"Please wait {remaining}s before next request", "red")
                return
            
            self.ros_node.publish_dispense_request(ppe_name)
            self.ros_node.publish_gate_status(self.safety_gate_locked)
            
            self.last_dispense_time = current_time
            
            self.ppe_buttons[ppe_name].setEnabled(False)
            QTimer.singleShot(int(self.dispense_cooldown * 1000), 
                            lambda: self.ppe_buttons[ppe_name].setEnabled(True))
            
            self.show_status(f"Requesting {ppe_name.title()}...", "blue")
        
        self.update_safety_gate()
        self.update_status_displays()

    def update_countdown(self):
        """Update the override countdown display"""
        self.time_remaining -= 1
        if self.time_remaining > 0:
            self.show_status(f"Override active: {int(self.time_remaining)}s", "orange")
        else:
            self.countdown_timer.stop()
            self.reset_override()

    def reset_override(self):
        """Reset system after override period"""
        for ppe in self.ppe_status:
            self.ppe_status[ppe] = False
        
        self.safety_gate_locked = True
        self.ros_node.publish_gate_status(self.safety_gate_locked)
        self.ppe_buttons['override'].setEnabled(True)
        
        self.countdown_timer.stop()
        
        self.show_status("Override period ended", "blue")
        self.update_status_displays()

    def show_status(self, message, color="black"):
        """Show status message with color and auto-reset"""
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"""
            color: {color};
            font-weight: bold;
        """)
        # Only start auto-reset timer if not in override countdown
        if "Override active" not in message:
            self.status_timer.start(3000)

    def reset_status(self):
        """Reset status message to default"""
        self.status_label.setText('Ready to dispense...')  # No "Status: " prefix
        self.status_label.setStyleSheet("color: black;")

    def update_safety_gate(self):
        """Update safety gate based on PPE detection"""
        previous_state = self.safety_gate_locked
        self.safety_gate_locked = not all(self.ppe_status.values())
        
        if previous_state != self.safety_gate_locked:
            # Emit signal instead of directly publishing
            self.gate_status_signal.emit(self.safety_gate_locked)

    def parse_ppe_status(self, status_str):
        """Parse PPE status string into dictionary - called from ROS thread"""
        # Emit signal instead of directly updating GUI
        self.status_update_signal.emit(status_str)

    def handle_status_update(self, status_str):
        """Handle PPE status updates in the Qt thread"""
        try:
            status_parts = status_str.split(',')
            for part in status_parts:
                name, value = part.strip().split(':')
                bool_value = value.strip().lower() == 'true'
                if name.strip() in self.ppe_status:
                    self.ppe_status[name.strip()] = bool_value
            
            self.update_safety_gate()
            self.update_status_displays()
            self.show_status("PPE status updated", "green")
        except Exception as e:
            self.ros_node.get_logger().error(f'Error parsing PPE status: {e}')
            self.show_status("Error updating PPE status", "red")

    def handle_gate_status(self, is_locked):
        """Handle gate status updates in the Qt thread"""
        if not self.is_shutting_down:
            self.ros_node.publish_gate_status(is_locked)

    def cleanup(self):
        """Clean up timers from the Qt thread"""
        if not self.is_shutting_down:
            self.is_shutting_down = True
            self.timer.stop()
            self.override_timer.stop()
            self.countdown_timer.stop()
            self.status_timer.stop()
            QApplication.processEvents()

    def closeEvent(self, event):
        """Handle window close event"""
        self.cleanup()
        event.accept()

    def update_status_displays(self):
        """Update all status displays"""
        if self.is_shutting_down:
            return
            
        try:
            # Update button colors and indicators
            for ppe, status in self.ppe_status.items():
                if ppe in self.ppe_buttons:
                    button = self.ppe_buttons[ppe].layout().itemAt(0).widget()
                    indicator = self.ppe_buttons[ppe].layout().itemAt(1).widget()
                    
                    # Update button color
                    if status:
                        button.setStyleSheet("""
                            QPushButton {
                                background-color: #4caf50;
                                color: white;
                                border: none;
                                border-radius: 5px;
                                font-weight: bold;
                            }
                            QPushButton:hover {
                                background-color: #45a049;
                            }
                            QPushButton:pressed {
                                background-color: #3d8b40;
                            }
                            QPushButton:disabled {
                                background-color: #cccccc;
                            }
                        """)
                    else:
                        button.setStyleSheet("""
                            QPushButton {
                                background-color: #ff6b6b;
                                color: white;
                                border: none;
                                border-radius: 5px;
                                font-weight: bold;
                            }
                            QPushButton:hover {
                                background-color: #ff5252;
                            }
                            QPushButton:pressed {
                                background-color: #ff3838;
                            }
                            QPushButton:disabled {
                                background-color: #cccccc;
                            }
                        """)
                    
                    # Update indicator visibility and content
                    if self.accessibility_mode:
                        indicator.show()
                        indicator.setText('O' if status else 'X')
                        indicator.setStyleSheet(f'color: {"green" if status else "red"};')
                    else:
                        indicator.hide()
            
            # Special styling for override button
            if 'override' in self.ppe_buttons:
                override_button = self.ppe_buttons['override'].layout().itemAt(0).widget()
                override_button.setStyleSheet("""
                    QPushButton {
                        background-color: #ff9800;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #f57c00;
                    }
                    QPushButton:pressed {
                        background-color: #ef6c00;
                    }
                    QPushButton:disabled {
                        background-color: #cccccc;
                    }
                """)
            
            # Update gate status
            self.gate_status.setText('Gate LOCKED' if self.safety_gate_locked else 'Gate UNLOCKED')
            self.gate_status.setStyleSheet(f"""
                QLabel {{
                    color: {'red' if self.safety_gate_locked else 'green'};
                    font-weight: bold;
                    padding: 5px;
                    font-size: 20pt;
                }}
            """)
        except Exception as e:
            if not self.is_shutting_down:
                print(f"Error updating status displays: {e}")

    def show_help(self):
        """Show the help dialog"""
        help_dialog = HelpDialog(self)
        help_dialog.exec_()

def main():
    with ros_context():
        ros_node = ROSNode()
        
        os.environ['XDG_RUNTIME_DIR'] = '/tmp/runtime-dir'
        app = QApplication(sys.argv)
        gui = ExperimentalPPEVendingMachine(ros_node)
        
        ros_node.gui = gui
        
        def spin_ros():
            try:
                while not gui.is_shutting_down:
                    if rclpy.ok():
                        rclpy.spin_once(ros_node, timeout_sec=0.1)
                    else:
                        break
            except Exception as e:
                if not gui.is_shutting_down:
                    print(f"ROS thread error: {e}")
        
        ros_thread = threading.Thread(target=spin_ros, daemon=True)
        ros_thread.start()
        
        def shutdown():
            if not gui.is_shutting_down:
                gui.is_shutting_down = True
                gui.cleanup()
                if rclpy.ok():
                    ros_node.destroy_node()
        
        def signal_handler(signum, frame):
            shutdown()
            app.quit()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            exit_code = app.exec_()
        except KeyboardInterrupt:
            shutdown()
            exit_code = 0
        except Exception as e:
            print(f"Error in main loop: {e}")
            shutdown()
            exit_code = 1
        finally:
            shutdown()
            sys.exit(exit_code)

if __name__ == '__main__':
    main() 