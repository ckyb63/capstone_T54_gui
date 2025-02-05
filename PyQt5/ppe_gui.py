#!/usr/bin/env python3
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QWidget, 
                            QGridLayout, QLabel, QVBoxLayout, QHBoxLayout,
                            QMessageBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool
import threading
import time

class PPEVendingMachine(QMainWindow):
    def __init__(self, ros_node):
        super().__init__()
        self.ros_node = ros_node
        self.initUI()
        
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
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Title
        title = QLabel('PPE Vending Machine')
        title.setFont(QFont('Arial', 24))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Status display
        self.status_label = QLabel('Status: Ready to dispense...')
        self.status_label.setFont(QFont('Arial', 14))
        layout.addWidget(self.status_label)
        
        # Gate status
        self.gate_status = QLabel('LOCKED')
        self.gate_status.setFont(QFont('Arial', 14))
        layout.addWidget(self.gate_status)
        
        # Camera feed placeholder
        camera_placeholder = QLabel('Camera Feed Placeholder')
        camera_placeholder.setStyleSheet("""
            QLabel {
                border: 2px dashed #666;
                background: #f0f0f0;
                min-height: 300px;
            }
        """)
        camera_placeholder.setAlignment(Qt.AlignCenter)
        layout.addWidget(camera_placeholder)
        
        # Add countdown label
        self.countdown_label = QLabel('')
        self.countdown_label.setFont(QFont('Arial', 12))
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.countdown_label.setStyleSheet('color: orange;')
        layout.addWidget(self.countdown_label)
        
        # PPE Buttons Grid
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        
        # Create PPE buttons with status indicators
        self.ppe_buttons = {}
        self.ppe_status_labels = {}
        
        ppe_items = [
            ('Hard Hat', 'hardhat', 0, 0),
            ('Beard Net', 'beardnet', 0, 1),
            ('Gloves', 'gloves', 0, 2),
            ('Safety Glasses', 'glasses', 1, 0),
            ('Ear Plugs', 'earplugs', 1, 1),
            ('OVERRIDE', 'override', 1, 2)
        ]
        
        for label, key, row, col in ppe_items:
            # Container for button and status
            container = QWidget()
            container_layout = QHBoxLayout(container)
            
            # Button
            button = QPushButton(label)
            button.setFont(QFont('Arial', 12))
            button.setMinimumHeight(60)
            button.clicked.connect(lambda checked, k=key: self.on_ppe_button_click(k))
            self.ppe_buttons[key] = button
            container_layout.addWidget(button, stretch=4)
            
            # Status indicator
            status_label = QLabel('X')
            status_label.setFont(QFont('Arial', 16, QFont.Bold))
            status_label.setAlignment(Qt.AlignCenter)
            status_label.setStyleSheet('color: red;')
            self.ppe_status_labels[key] = status_label
            container_layout.addWidget(status_label, stretch=1)
            
            grid.addWidget(container, row, col)
        
        layout.addWidget(grid_widget)
        
        # Window setup
        self.setWindowTitle('PPE Vending Machine')
        self.setGeometry(100, 100, 800, 600)
        self.show()

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
            # Show confirmation dialog
            if not self.confirm_override():
                return
                
            # Set all PPE to detected
            for ppe in self.ppe_status:
                self.ppe_status[ppe] = True
            self.safety_gate_locked = False
            
            # Publish override request
            self.ros_node.publish_dispense_request('OVERRIDE')
            
            # Publish gate status
            self.ros_node.publish_gate_status(self.safety_gate_locked)
            
            # Disable override button
            self.ppe_buttons['override'].setEnabled(False)
            
            # Start override timer
            self.override_timer.start(int(self.override_duration * 1000))
            
            # Start countdown
            self.time_remaining = self.override_duration
            self.update_countdown()
            self.countdown_timer.start()
            
            # Show status with countdown
            self.show_status(f"Override activated for {int(self.override_duration)}s!", "green")
            
        else:
            # Check cooldown
            if current_time - self.last_dispense_time < self.dispense_cooldown:
                remaining = round(self.dispense_cooldown - (current_time - self.last_dispense_time), 1)
                self.show_status(f"Please wait {remaining}s before next request", "red")
                return
            
            # Publish dispense request
            self.ros_node.publish_dispense_request(ppe_name)
            
            # Publish current gate status
            self.ros_node.publish_gate_status(self.safety_gate_locked)
            
            self.last_dispense_time = current_time
            
            # Update button state
            self.ppe_buttons[ppe_name].setEnabled(False)
            QTimer.singleShot(int(self.dispense_cooldown * 1000), 
                            lambda: self.ppe_buttons[ppe_name].setEnabled(True))
            
            # Show status
            self.show_status(f"Dispensing {ppe_name.title()}...", "blue")
        
        # Update safety gate status
        self.update_safety_gate()
        
        # Update display
        self.update_status_displays()

    def update_countdown(self):
        """Update the override countdown display"""
        self.time_remaining -= 1
        if self.time_remaining > 0:
            self.countdown_label.setText(f"Override active: {int(self.time_remaining)}s remaining")
        else:
            self.countdown_label.setText("")
            self.countdown_timer.stop()

    def reset_override(self):
        """Reset system after override period"""
        # Reset all PPE status
        for ppe in self.ppe_status:
            self.ppe_status[ppe] = False
        
        # Reset safety gate
        self.safety_gate_locked = True
        
        # Publish gate status on reset
        self.ros_node.publish_gate_status(self.safety_gate_locked)
        
        # Re-enable override button
        self.ppe_buttons['override'].setEnabled(True)
        
        # Clear countdown
        self.countdown_label.setText("")
        self.countdown_timer.stop()
        
        # Show status
        self.show_status("Override period ended", "blue")
        
        # Update display
        self.update_status_displays()

    def show_status(self, message, color="black"):
        """Show status message with color and auto-reset"""
        self.status_label.setText(f"Status: {message}")
        self.status_label.setStyleSheet(f"color: {color};")
        
        # Reset status after 3 seconds
        self.status_timer.start(3000)

    def reset_status(self):
        """Reset status message to default"""
        self.status_label.setText("Status: Ready to dispense...")
        self.status_label.setStyleSheet("color: black;")

    def update_safety_gate(self):
        """Update safety gate based on PPE detection"""
        previous_state = self.safety_gate_locked
        self.safety_gate_locked = not all(self.ppe_status.values())
        
        # If state changed, publish new state
        if previous_state != self.safety_gate_locked:
            self.ros_node.publish_gate_status(self.safety_gate_locked)

    def update_status_displays(self):
        """Update all status displays"""
        # Update PPE status indicators
        for ppe, status in self.ppe_status.items():
            if ppe in self.ppe_status_labels:
                if status:
                    self.ppe_status_labels[ppe].setText('O')
                    self.ppe_status_labels[ppe].setStyleSheet('color: green;')
                else:
                    self.ppe_status_labels[ppe].setText('X')
                    self.ppe_status_labels[ppe].setStyleSheet('color: red;')
        
        # Update gate status
        self.gate_status.setText('LOCKED' if self.safety_gate_locked else 'UNLOCKED')
        self.gate_status.setStyleSheet(
            'color: red;' if self.safety_gate_locked else 'color: green;'
        )

    def parse_ppe_status(self, status_str):
        """Parse PPE status string into dictionary"""
        try:
            # Split the string into individual PPE statuses
            status_parts = status_str.split(',')
            for part in status_parts:
                # Split each part into name and value
                name, value = part.strip().split(':')
                # Convert string 'True'/'False' to boolean
                bool_value = value.strip().lower() == 'true'
                # Update status if name is valid
                if name.strip() in self.ppe_status:
                    self.ppe_status[name.strip()] = bool_value
            
            # Update safety gate after parsing
            self.update_safety_gate()
            
            # Publish current gate status after update
            self.ros_node.publish_gate_status(self.safety_gate_locked)
            
            # Update display
            self.update_status_displays()
            # Show status message
            self.show_status("PPE status updated", "green")
        except Exception as e:
            self.ros_node.get_logger().error(f'Error parsing PPE status: {e}')
            self.show_status("Error updating PPE status", "red")

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
        if self.gui:
            self.gui.parse_ppe_status(msg.data)
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

def main():
    # Initialize ROS
    rclpy.init(args=None)
    ros_node = ROSNode()
    
    # Initialize Qt
    app = QApplication(sys.argv)
    gui = PPEVendingMachine(ros_node)
    
    # Connect GUI to ROS node
    ros_node.gui = gui
    
    # Create and start ROS spin thread
    def spin_ros():
        rclpy.spin(ros_node)
        ros_node.destroy_node()
        rclpy.shutdown()
    
    ros_thread = threading.Thread(target=spin_ros, daemon=True)
    ros_thread.start()
    
    # Start Qt event loop
    exit_code = app.exec_()
    
    # Cleanup
    rclpy.shutdown()
    sys.exit(exit_code)

if __name__ == '__main__':
    main()