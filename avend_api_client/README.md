# AVend API Client

A PySide6-based GUI application for interacting with the AVend Local Dispense API.

## Features

- Connect to AVend middleware with configurable host and port
- Start vending sessions
- Single-item dispensing
- Multi-item cart functionality (add, remove, clear, dispense)
- Quick dispense buttons for common selections
- Response logging

## Requirements

- Python 3.6+
- PySide6
- Requests

## Installation

1. Install the required dependencies:

```
pip install -r requirements.txt
```

## Usage

1. Run the GUI application:

```
python avend_gui.py
```

2. Configure the connection settings (default: 127.0.0.1:8080)
3. Click "Connect" to initialize the API client
4. Start a session before performing any dispense operations
5. Use the various controls to interact with the vending machine:
   - Direct dispense: Enter a code and click "Dispense"
   - Cart operations: Add items to cart, then dispense them all at once
   - Quick dispense: Click any of the numbered buttons for one-click dispensing

## API Documentation

The `AvendAPI` class provides a Python interface to the AVend Local Dispense API:

- `start_session()` - Start a new vending session
- `dispense(code=None, mode=None)` - Dispense an item or the cart contents
- `add_to_cart(code)` - Add an item to the cart
- `remove_from_cart(code)` - Remove an item from the cart
- `clear_cart()` - Clear all items from the cart
- `get_info()` - Get information about the current configuration

## Notes

- A session must be started before any dispense operations
- Sessions timeout after 5 minutes of inactivity
- For special characters like * or #, the API handles URL encoding automatically
