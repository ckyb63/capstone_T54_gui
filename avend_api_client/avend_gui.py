"""
PySide 6 Client Test Application for the AVend Local Dispense API
Max Chen - v0.3.1
"""

import sys
import requests  # Add this import
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QTextEdit, QGridLayout, QGroupBox,
    QFormLayout, QSpinBox, QComboBox, QMessageBox, QLabel
)
from PySide6.QtCore import Qt, QTimer
from avend_api import AvendAPI

class AvendGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AVend API Client")
        self.setMinimumSize(800, 600)
        
        # Initialize API client with default values
        self.api = AvendAPI()
        
        # Set up the UI
        self.setup_ui()
    
    def setup_ui(self):
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Connection settings
        connection_group = QGroupBox("Connection Settings")
        connection_layout = QFormLayout()
        
        # Add connection settings
        self.host_input = QLineEdit("10.165.101.252")
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(8080)
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_to_api)
        
        connection_layout.addRow("Host:", self.host_input)
        connection_layout.addRow("Port:", self.port_input)
        connection_layout.addRow("", self.connect_button)
        connection_group.setLayout(connection_layout)
        
        # Second Server Connection settings
        second_server_group = QGroupBox("Second Server Connection (for '8' button)")
        second_server_layout = QFormLayout()
        self.second_host_input = QLineEdit("localhost") # Default host for second server
        self.second_port_input = QSpinBox()
        self.second_port_input.setRange(1, 65535)
        self.second_port_input.setValue(8081) # Default port for second server
        second_server_layout.addRow("Host:", self.second_host_input)
        second_server_layout.addRow("Port:", self.second_port_input)
        self.second_connect_button = QPushButton("Connect Second Server")
        self.second_connect_button.clicked.connect(self.connect_to_second_server)
        second_server_layout.addRow("", self.second_connect_button)
        second_server_group.setLayout(second_server_layout)
        
        # Session control
        session_group = QGroupBox("Session Control")
        session_layout = QVBoxLayout()
        
        # Add session control buttons
        self.start_session_button = QPushButton("Start Session")
        self.start_session_button.clicked.connect(self.start_session)
        self.get_info_button = QPushButton("Get Info")
        self.get_info_button.clicked.connect(self.get_info)
        
        session_layout.addWidget(self.start_session_button)
        session_layout.addWidget(self.get_info_button)
        session_group.setLayout(session_layout)
        
        # Dispense controls
        dispense_group = QGroupBox("Dispense Controls")
        dispense_layout = QFormLayout()
        
        # Add dispense controls
        self.dispense_code_input = QLineEdit()
        self.dispense_mode_combo = QComboBox()
        self.dispense_mode_combo.addItems(["double", "single"])
        self.dispense_button = QPushButton("Dispense")
        self.dispense_button.clicked.connect(self.dispense)
        
        dispense_layout.addRow("Code:", self.dispense_code_input)
        dispense_layout.addRow("Mode:", self.dispense_mode_combo)
        dispense_layout.addRow("", self.dispense_button)
        dispense_group.setLayout(dispense_layout)
        
        # Cart controls
        cart_group = QGroupBox("Cart Controls")
        cart_layout = QFormLayout()
        
        # Add cart controls
        self.cart_code_input = QLineEdit()
        
        cart_buttons_layout = QHBoxLayout()
        self.add_to_cart_button = QPushButton("Add to Cart")
        self.add_to_cart_button.clicked.connect(self.add_to_cart)
        self.remove_from_cart_button = QPushButton("Remove from Cart")
        self.remove_from_cart_button.clicked.connect(self.remove_from_cart)
        self.clear_cart_button = QPushButton("Clear Cart")
        self.clear_cart_button.clicked.connect(self.clear_cart)
        self.dispense_cart_button = QPushButton("Dispense Cart")
        self.dispense_cart_button.clicked.connect(self.dispense_cart)
        
        cart_buttons_layout.addWidget(self.add_to_cart_button)
        cart_buttons_layout.addWidget(self.remove_from_cart_button)
        cart_buttons_layout.addWidget(self.clear_cart_button)
        cart_buttons_layout.addWidget(self.dispense_cart_button)
        
        cart_layout.addRow("Code:", self.cart_code_input)
        cart_layout.addRow("", cart_buttons_layout)
        cart_group.setLayout(cart_layout)
        
        # Quick dispense buttons
        quick_dispense_group = QGroupBox("Quick Dispense")
        quick_dispense_layout = QGridLayout()
        
        # Add quick dispense keypad
        self.quick_buttons = []
        
        # Row labels (A-G)
        row_labels = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        
        # Add row label buttons
        for i, label in enumerate(row_labels):
            btn = QPushButton(label)
            btn.setEnabled(False)  # Make row labels non-clickable
            btn.setStyleSheet("background-color: #e0e0e0;")
            quick_dispense_layout.addWidget(btn, i+1, 0)
        
        # Add column label buttons (1-9)
        for j in range(1, 10):
            btn = QPushButton(str(j))
            btn.setEnabled(False)  # Make column labels non-clickable
            btn.setStyleSheet("background-color: #e0e0e0;")
            quick_dispense_layout.addWidget(btn, 0, j)
        
        # Add combination buttons (A1-G9)
        for i, row_label in enumerate(row_labels):
            for j in range(1, 10):
                code = f"{row_label}{j}"
                btn = QPushButton(code)
                btn.clicked.connect(lambda checked, code=code: self.quick_dispense(code))
                quick_dispense_layout.addWidget(btn, i+1, j)
                self.quick_buttons.append(btn)
        
        # Add special buttons (0, *, #, H, J) in an additional row
        # Place the '8' button first in the special keys row
        btn_8 = QPushButton("8")
        btn_8.clicked.connect(lambda: self.send_to_second_server("8"))
        quick_dispense_layout.addWidget(btn_8, len(row_labels)+1, 1) # Add '8' at column 1
        self.quick_buttons.append(btn_8)

        special_keys = ['0', '*', '#', 'H', 'J']
        for j, key in enumerate(special_keys):
            # Use HTML URL encoding for special characters in the API call
            display_key = key
            api_key = key
            if key == '*':
                api_key = '%2A'  # URL encoded asterisk
            elif key == '#':
                api_key = '%23'  # URL encoded hash
            
            btn = QPushButton(display_key)
            btn.clicked.connect(lambda checked, code=api_key: self.quick_dispense(code))
            # Shift other special keys to start from column 2
            quick_dispense_layout.addWidget(btn, len(row_labels)+1, j+2) 
            self.quick_buttons.append(btn)
        
        quick_dispense_group.setLayout(quick_dispense_layout)
        
        # Add log area
        log_group = QGroupBox("Response Log")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        
        # Service routine controls
        service_group = QGroupBox("H1 Service Routine")
        service_layout = QFormLayout()
        
        # Add service routine controls
        self.service_interval_input = QSpinBox()
        self.service_interval_input.setRange(1, 60)
        self.service_interval_input.setValue(15)  # Default to 15 seconds
        self.service_interval_input.setSuffix(" seconds")
        
        self.service_status_label = QLabel("Status: Not running")
        
        service_buttons_layout = QHBoxLayout()
        self.start_service_button = QPushButton("Start H1 Service")
        self.start_service_button.clicked.connect(self.start_service_routine)
        self.stop_service_button = QPushButton("Stop H1 Service")
        self.stop_service_button.clicked.connect(self.stop_service_routine)
        self.stop_service_button.setEnabled(False)
        
        service_buttons_layout.addWidget(self.start_service_button)
        service_buttons_layout.addWidget(self.stop_service_button)
        
        service_layout.addRow("Interval:", self.service_interval_input)
        service_layout.addRow("Status:", self.service_status_label)
        service_layout.addRow("", service_buttons_layout)
        
        service_group.setLayout(service_layout)
        
        # Add all groups to main layout
        top_layout = QHBoxLayout()
        top_layout.addWidget(connection_group)
        top_layout.addWidget(second_server_group)
        top_layout.addWidget(session_group)
        
        middle_layout = QHBoxLayout()
        middle_layout.addWidget(dispense_group)
        middle_layout.addWidget(cart_group)
        middle_layout.addWidget(service_group)
        
        main_layout.addLayout(top_layout)
        main_layout.addLayout(middle_layout)
        main_layout.addWidget(quick_dispense_group)
        main_layout.addWidget(log_group)
    
    def log_message(self, message):
        """Add a message to the log area"""
        self.log_text.append(message)
        # Scroll to the bottom
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def connect_to_api(self):
        """Update the API connection settings and start a session"""
        host = self.host_input.text()
        port = self.port_input.value()
        
        self.api = AvendAPI(host=host, port=port)
        self.log_message(f"Updated primary API connection to {host}:{port}")
        # Also attempt to start a session
        self.start_session()
    
    def connect_to_second_server(self):
        """Test connection and attempt to start a session on the second server."""
        host = self.second_host_input.text()
        port = self.second_port_input.value()
        url = f"http://{host}:{port}/start_session" # Assuming /start_session endpoint
        
        self.log_message(f"Connecting to second server at {host}:{port} and starting session...")
        
        try:
            response = requests.get(url, timeout=5) 
            response.raise_for_status()
            
            self.log_message(f"Second server session response: {response.status_code} - {response.text}")
            # Optionally display success message
            # QMessageBox.information(self, "Second Server", f"Connected and session started on second server: {response.text}")
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Error connecting/starting session on second server: {e}"
            self.log_message(error_msg)
            QMessageBox.critical(self, "Second Server Error", error_msg)

    def start_session(self):
        """Start a new session on the primary API"""
        self.log_message("Starting new primary session...")
        response = self.api.start_session()
        
        if response.get("success", False):
            self.log_message("Session started successfully")
        else:
            error_msg = response.get("error", f"Status code: {response.get('status_code')}")
            self.log_message(f"Failed to start session: {error_msg}")
            QMessageBox.warning(self, "Session Error", f"Failed to start session: {error_msg}")
    
    def get_info(self):
        """Get API info"""
        self.log_message("Getting API info...")
        response = self.api.get_info()
        
        if response.get("success", False):
            self.log_message(f"API Info: {response.get('response', '')}")
        else:
            error_msg = response.get("error", f"Status code: {response.get('status_code')}")
            self.log_message(f"Failed to get info: {error_msg}")
    
    def dispense(self):
        """Dispense a specific item"""
        code = self.dispense_code_input.text()
        mode = self.dispense_mode_combo.currentText()
        
        if not code:
            QMessageBox.warning(self, "Input Error", "Please enter a dispense code")
            return
        
        self.log_message(f"Dispensing code {code} with mode {mode}...")
        response = self.api.dispense(code=code, mode=mode)
        
        if response.get("success", False):
            self.log_message(f"Dispensed successfully: {response.get('response', '')}")
        else:
            error_msg = response.get("error", f"Status code: {response.get('status_code')}")
            self.log_message(f"Failed to dispense: {error_msg}")
            QMessageBox.warning(self, "Dispense Error", f"Failed to dispense: {error_msg}")
    
    def add_to_cart(self):
        """Add an item to the cart"""
        code = self.cart_code_input.text()
        
        if not code:
            QMessageBox.warning(self, "Input Error", "Please enter a code to add to cart")
            return
        
        self.log_message(f"Adding code {code} to cart...")
        response = self.api.add_to_cart(code=code)
        
        if response.get("success", False):
            self.log_message(f"Added to cart successfully: {response.get('response', '')}")
        else:
            error_msg = response.get("error", f"Status code: {response.get('status_code')}")
            self.log_message(f"Failed to add to cart: {error_msg}")
    
    def remove_from_cart(self):
        """Remove an item from the cart"""
        code = self.cart_code_input.text()
        
        if not code:
            QMessageBox.warning(self, "Input Error", "Please enter a code to remove from cart")
            return
        
        self.log_message(f"Removing code {code} from cart...")
        response = self.api.remove_from_cart(code=code)
        
        if response.get("success", False):
            self.log_message(f"Removed from cart successfully: {response.get('response', '')}")
        else:
            error_msg = response.get("error", f"Status code: {response.get('status_code')}")
            self.log_message(f"Failed to remove from cart: {error_msg}")
    
    def clear_cart(self):
        """Clear the cart"""
        self.log_message("Clearing cart...")
        response = self.api.clear_cart()
        
        if response.get("success", False):
            self.log_message(f"Cart cleared successfully: {response.get('response', '')}")
        else:
            error_msg = response.get("error", f"Status code: {response.get('status_code')}")
            self.log_message(f"Failed to clear cart: {error_msg}")
    
    def dispense_cart(self):
        """Dispense all items in the cart"""
        self.log_message("Dispensing cart...")
        response = self.api.dispense()
        
        if response.get("success", False):
            self.log_message(f"Cart dispensed successfully: {response.get('response', '')}")
        else:
            error_msg = response.get("error", f"Status code: {response.get('status_code')}")
            self.log_message(f"Failed to dispense cart: {error_msg}")
            QMessageBox.warning(self, "Dispense Error", f"Failed to dispense cart: {error_msg}")
    
    def quick_dispense(self, code):
        """Quick dispense a specific item (includes starting a session)"""
        # First start a session
        self.log_message(f"Quick dispense: Starting session for code {code}...")
        session_response = self.api.start_session()
        
        if not session_response.get("success", False):
            error_msg = session_response.get("error", f"Status code: {session_response.get('status_code')}")
            self.log_message(f"Failed to start session: {error_msg}")
            QMessageBox.warning(self, "Session Error", f"Failed to start session: {error_msg}")
            return
        
        # Then dispense the item
        self.log_message(f"Quick dispense: Dispensing code {code}...")
        dispense_response = self.api.dispense(code=code)
        
        if dispense_response.get("success", False):
            self.log_message(f"Dispensed successfully: {dispense_response.get('response', '')}")
        else:
            error_msg = dispense_response.get("error", f"Status code: {dispense_response.get('status_code')}")
            self.log_message(f"Failed to dispense: {error_msg}")
            QMessageBox.warning(self, "Dispense Error", f"Failed to dispense: {error_msg}")
            
    def send_to_second_server(self, data):
        """Send data (e.g., '8') to the second server."""
        host = self.second_host_input.text()
        port = self.second_port_input.value()
        # Use the /dispense endpoint
        url = f"http://{host}:{port}/dispense" 
        
        self.log_message(f"Sending '{data}' to second server at {url}...")
        
        try:
            # Send a GET request with the data, adjust method/params as needed
            response = requests.get(url, params={'data': data}, timeout=5) 
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            
            self.log_message(f"Second server response: {response.status_code} - {response.text}")
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Error sending to second server: {e}"
            self.log_message(error_msg)
            QMessageBox.critical(self, "Second Server Error", error_msg)

    def start_service_routine(self):
        """Start the H1 service routine"""
        interval = self.service_interval_input.value()
        
        self.log_message(f"Starting H1 service routine (interval: {interval}s, running indefinitely)...")
        response = self.api.start_service_routine(interval=interval)
        
        if response.get("success", False):
            self.log_message(f"Service routine started: {response.get('message', '')}")
            self.service_status_label.setText("Status: Running (indefinitely)")
            self.start_service_button.setEnabled(False)
            self.stop_service_button.setEnabled(True)
        else:
            self.log_message(f"Failed to start service routine: {response.get('error', '')}")
    
    def stop_service_routine(self):
        """Stop the H1 service routine"""
        self.log_message("Stopping H1 service routine...")
        response = self.api.stop_service_routine()
        
        if response.get("success", False):
            self.log_message(f"Service routine stopped: {response.get('message', '')}")
            self.service_routine_completed()
    
    def service_routine_completed(self):
        """Called when the service routine completes"""
        self.service_status_label.setText("Status: Not running")
        self.start_service_button.setEnabled(True)
        self.stop_service_button.setEnabled(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AvendGUI()
    window.showMaximized()
    sys.exit(app.exec())
