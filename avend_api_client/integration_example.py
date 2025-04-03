"""
Example of integrating AVend API with an existing PySide application.
This shows how to connect buttons in your application to the AVend API.
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QPushButton, QLineEdit, QLabel, QGridLayout, QMessageBox
)
from PySide6.QtCore import Qt
from avend_api import AvendAPI

class ExistingAppWithAVendIntegration(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AVend API Integration Example")
        self.setMinimumSize(500, 400)
        
        # Initialize the AVend API client
        # Replace with your actual AVend middleware host and port
        self.avend_api = AvendAPI(host="127.0.0.1", port=8080)
        
        # Set up the UI
        self.setup_ui()
    
    def setup_ui(self):
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Add a label
        main_layout.addWidget(QLabel("Product Selection"))
        
        # Create a grid of product buttons
        products_grid = QGridLayout()
        
        # Define some example products with their codes
        self.products = [
            {"name": "Product A", "code": "01"},
            {"name": "Product B", "code": "02"},
            {"name": "Product C", "code": "03"},
            {"name": "Product D", "code": "04"},
            {"name": "Product E", "code": "05"},
            {"name": "Product F", "code": "06"},
            {"name": "Product G", "code": "07"},
            {"name": "Product H", "code": "08"},
            {"name": "Product I", "code": "09"},
        ]
        
        # Create buttons for each product
        row, col = 0, 0
        for product in self.products:
            button = QPushButton(f"{product['name']} ({product['code']})")
            # Connect the button to the dispense function with the product code
            button.clicked.connect(lambda checked, code=product['code']: self.dispense_product(code))
            products_grid.addWidget(button, row, col)
            
            # Move to the next column or row
            col += 1
            if col > 2:  # 3 columns per row
                col = 0
                row += 1
        
        main_layout.addLayout(products_grid)
        
        # Add a status label
        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)
    
    def dispense_product(self, code):
        """
        Handle product dispensing when a button is clicked
        
        Args:
            code (str): The product code to dispense
        """
        self.status_label.setText(f"Dispensing product {code}...")
        
        # First start a session (required before any dispense operation)
        session_response = self.avend_api.start_session()
        
        if not session_response.get("success", False):
            error_msg = session_response.get("error", "Failed to start session")
            self.status_label.setText(f"Error: {error_msg}")
            QMessageBox.warning(self, "Session Error", f"Failed to start session: {error_msg}")
            return
        
        # Then dispense the product
        dispense_response = self.avend_api.dispense(code=code)
        
        if dispense_response.get("success", False):
            self.status_label.setText(f"Successfully dispensed product {code}")
        else:
            error_msg = dispense_response.get("error", "Failed to dispense product")
            self.status_label.setText(f"Error: {error_msg}")
            QMessageBox.warning(self, "Dispense Error", f"Failed to dispense: {error_msg}")


# For multi-product dispensing
class MultiProductExample(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Product Dispense Example")
        self.setMinimumSize(500, 400)
        
        # Initialize the AVend API client
        self.avend_api = AvendAPI(host="127.0.0.1", port=8080)
        
        # Keep track of products in cart
        self.cart = []
        
        # Set up the UI
        self.setup_ui()
    
    def setup_ui(self):
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Add a label
        main_layout.addWidget(QLabel("Add Products to Cart"))
        
        # Create a grid of product buttons
        products_grid = QGridLayout()
        
        # Define some example products with their codes
        self.products = [
            {"name": "Product A", "code": "01"},
            {"name": "Product B", "code": "02"},
            {"name": "Product C", "code": "03"},
            {"name": "Product D", "code": "04"},
            {"name": "Product E", "code": "05"},
            {"name": "Product F", "code": "06"},
        ]
        
        # Create buttons for each product
        row, col = 0, 0
        for product in self.products:
            button = QPushButton(f"{product['name']} ({product['code']})")
            # Connect the button to add the product to the cart
            button.clicked.connect(lambda checked, code=product['code'], name=product['name']: 
                                  self.add_to_cart(code, name))
            products_grid.addWidget(button, row, col)
            
            # Move to the next column or row
            col += 1
            if col > 2:  # 3 columns per row
                col = 0
                row += 1
        
        main_layout.addLayout(products_grid)
        
        # Cart display
        main_layout.addWidget(QLabel("Cart:"))
        self.cart_display = QLabel("Empty")
        main_layout.addWidget(self.cart_display)
        
        # Dispense cart button
        self.dispense_button = QPushButton("Dispense All Items")
        self.dispense_button.clicked.connect(self.dispense_cart)
        main_layout.addWidget(self.dispense_button)
        
        # Clear cart button
        self.clear_button = QPushButton("Clear Cart")
        self.clear_button.clicked.connect(self.clear_cart)
        main_layout.addWidget(self.clear_button)
        
        # Add a status label
        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)
    
    def add_to_cart(self, code, name):
        """Add a product to the cart"""
        self.status_label.setText(f"Adding {name} to cart...")
        
        # Check if we need to start a session first
        if not self.cart:
            session_response = self.avend_api.start_session()
            if not session_response.get("success", False):
                error_msg = session_response.get("error", "Failed to start session")
                self.status_label.setText(f"Error: {error_msg}")
                QMessageBox.warning(self, "Session Error", f"Failed to start session: {error_msg}")
                return
        
        # Add to the AVend cart
        response = self.avend_api.add_to_cart(code)
        
        if response.get("success", False):
            # Add to our local cart tracking
            self.cart.append({"code": code, "name": name})
            self.update_cart_display()
            self.status_label.setText(f"Added {name} to cart")
        else:
            error_msg = response.get("error", "Failed to add to cart")
            self.status_label.setText(f"Error: {error_msg}")
            QMessageBox.warning(self, "Cart Error", f"Failed to add to cart: {error_msg}")
    
    def update_cart_display(self):
        """Update the cart display"""
        if not self.cart:
            self.cart_display.setText("Empty")
        else:
            cart_text = ", ".join([f"{item['name']} ({item['code']})" for item in self.cart])
            self.cart_display.setText(cart_text)
    
    def dispense_cart(self):
        """Dispense all items in the cart"""
        if not self.cart:
            QMessageBox.information(self, "Empty Cart", "The cart is empty. Add some products first.")
            return
        
        self.status_label.setText("Dispensing all items...")
        
        # Dispense the cart
        response = self.avend_api.dispense()
        
        if response.get("success", False):
            self.status_label.setText("Successfully dispensed all items")
            # Clear our local cart tracking
            self.cart = []
            self.update_cart_display()
        else:
            error_msg = response.get("error", "Failed to dispense cart")
            self.status_label.setText(f"Error: {error_msg}")
            QMessageBox.warning(self, "Dispense Error", f"Failed to dispense cart: {error_msg}")
    
    def clear_cart(self):
        """Clear the cart"""
        if not self.cart:
            return
        
        self.status_label.setText("Clearing cart...")
        
        # Clear the AVend cart
        response = self.avend_api.clear_cart()
        
        if response.get("success", False):
            # Clear our local cart tracking
            self.cart = []
            self.update_cart_display()
            self.status_label.setText("Cart cleared")
        else:
            error_msg = response.get("error", "Failed to clear cart")
            self.status_label.setText(f"Error: {error_msg}")
            QMessageBox.warning(self, "Cart Error", f"Failed to clear cart: {error_msg}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Choose which example to run
    # window = ExistingAppWithAVendIntegration()  # Single product dispensing
    window = MultiProductExample()  # Multi-product dispensing
    
    window.show()
    sys.exit(app.exec())
