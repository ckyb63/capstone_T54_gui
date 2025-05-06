# AVend API Client

A PySide6-based GUI application for interacting with the AVend Local Dispense API.

## Requirements

- PySide6 (The test GUI)
- Requests

## Usage

1. Run the test GUI application:

   ```bash
   python avend_test_vend_gui.py
   ```

2. Configure the connection settings (default: 127.0.0.1:8080 which is local host)
3. Click "Connect" to initialize the API client
4. Start a session before performing any dispense operations
5. Use the various controls to interact with the vending machine:
   - Direct dispense: Enter a code and click "Dispense"
   - Cart operations: Add items to cart, then dispense them all at once
   - Quick dispense: Click any of the numbered buttons for one-click dispensing

## API Documentation

The `AvendAPI` class provides a Python interface to the AVend Local Dispense API:

- `__init__(host="127.0.0.1", port=8080)` - Initialize the API client with host and port
- `start_session()` - Start a new vending session
- `dispense(code=None, mode=None)` - Dispense an item or the cart contents
- `add_to_cart(code)` - Add an item to the cart
- `remove_from_cart(code)` - Remove an item from the cart
- `clear_cart()` - Clear all items from the cart
- `get_info()` - Get information about the current configuration
- `start_service_routine(interval=None)` - Start a routine that repeatedly dispenses H1
- `stop_service_routine()` - Stop the H1 service routine

## Notes

- A session must be started before any dispense operations
- Sessions timeout after 5 minutes of inactivity, which also turns off the Avend Kit.
- For special characters like * or #, the API handles URL encoding automatically
- A new cookie is generated for each start session and is only useed for that one dispense.
- The Service Routine is a work around for the SnackMart Vending Machine we are using, it calls the non-existent H1 product to keep the machine from escaping service mode.
- Normally you would only use start session and dispense.
