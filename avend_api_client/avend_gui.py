import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QTextEdit, QGridLayout, QGroupBox,
    QFormLayout, QSpinBox, QComboBox, QMessageBox
)
from PySide6.QtCore import Qt
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
        
        self.host_input = QLineEdit("127.0.0.1")
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(8080)
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_to_api)
        
        connection_layout.addRow("Host:", self.host_input)
        connection_layout.addRow("Port:", self.port_input)
        connection_layout.addRow("", self.connect_button)
        connection_group.setLayout(connection_layout)
        
        # Session control
        session_group = QGroupBox("Session Control")
        session_layout = QVBoxLayout()
        
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
        
        # Create a 5x5 grid of number buttons
        self.quick_buttons = []
        for i in range(5):
            for j in range(5):
                num = i * 5 + j + 1
                btn = QPushButton(str(num).zfill(2))
                btn.clicked.connect(lambda checked, code=str(num).zfill(2): self.quick_dispense(code))
                quick_dispense_layout.addWidget(btn, i, j)
                self.quick_buttons.append(btn)
        
        quick_dispense_group.setLayout(quick_dispense_layout)
        
        # Log area
        log_group = QGroupBox("Response Log")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        
        # Add all groups to main layout
        top_layout = QHBoxLayout()
        top_layout.addWidget(connection_group)
        top_layout.addWidget(session_group)
        
        middle_layout = QHBoxLayout()
        middle_layout.addWidget(dispense_group)
        middle_layout.addWidget(cart_group)
        
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
        """Update the API connection settings"""
        host = self.host_input.text()
        port = self.port_input.value()
        
        self.api = AvendAPI(host=host, port=port)
        self.log_message(f"Connected to AVend API at {host}:{port}")
    
    def start_session(self):
        """Start a new session"""
        self.log_message("Starting new session...")
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AvendGUI()
    window.show()
    sys.exit(app.exec())
