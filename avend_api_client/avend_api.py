"""
Python Client for the AVend Local Dispense API
Implements AVend Local Dispense API Guide v1.2.2
Max Chen - v0.3.2
"""

import requests
import threading
import time

class AvendAPI:
    def __init__(self, host="127.0.0.1", port=8080): # Defaults with the set LocalHost and Port
        self.base_url = f"http://{host}:{port}/avend"
        self.session = requests.Session()  # Keeps cookie between calls
        self.service_thread = None
        self.service_running = False
        self.service_interval = 20  # Default H1 Request Interval is 20s

    def start_session(self): # Start a new session
        params = {"action": "start"}
        try:
            response = self.session.get(self.base_url, params=params)
            return self._format_response(response)
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def dispense(self, code=None, mode=None): # Dispense a product by code
        params = {"action": "dispense"}
        if code:
            params["code"] = code
        if mode:
            params["mode"] = mode
        try:
            response = self.session.get(self.base_url, params=params)
            return self._format_response(response)
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def get_info(self): # Get information about the AVend middleware
        url = f"{self.base_url}/info"
        try:
            response = self.session.get(url)
            return self._format_response(response)
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def add_to_cart(self, code): # Add a product to the cart
        params = {"action": "add", "code": code}
        try:
            response = self.session.get(self.base_url, params=params)
            return self._format_response(response)
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def remove_from_cart(self, code): # Remove a product from the cart
        params = {"action": "remove", "code": code}
        try:
            response = self.session.get(self.base_url, params=params)
            return self._format_response(response)
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def clear_cart(self): # Clear the cart
        params = {"action": "clear"}
        try:
            response = self.session.get(self.base_url, params=params)
            return self._format_response(response)
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    # The _post method is removed as the AVend API uses GET requests with query parameters

    def _format_response(self, response): # Internal method for formatting responses
        try:
            return {
                "success": response.ok,
                "status_code": response.status_code,
                "response": response.json() if response.content else {}
            }
        except ValueError: # If the response is not JSON
            return {
                "success": response.ok,
                "status_code": response.status_code,
                "response": response.text
            }
            
    def start_service_routine(self, interval=None):
        """
        Start a service routine that will repeatedly dispense H1 until explicitly stopped
        
        Args:
            interval (int): Time in seconds between each H1 dispense call
        """
        if interval is not None:
            self.service_interval = interval
            
        # Stop any existing service routine
        self.stop_service_routine()
        
        # Start a new service routine
        self.service_running = True
        self.service_thread = threading.Thread(target=self._service_routine_worker)
        self.service_thread.daemon = True  # Thread will exit when main program exits
        self.service_thread.start()
        
        return {"success": True, "message": f"Service routine started with interval {self.service_interval}s (running indefinitely)"}
    
    def stop_service_routine(self):
        """Stop the service routine if it's running"""
        if self.service_running:
            self.service_running = False
            if self.service_thread and self.service_thread.is_alive():
                self.service_thread.join(timeout=1.0)  # Wait for thread to finish
            return {"success": True, "message": "Service routine stopped"}
        return {"success": True, "message": "No service routine was running"}
    
    def _service_routine_worker(self):
        """Worker function for the service routine thread that runs indefinitely"""
        
        while self.service_running:
            # Start a new session for each dispense
            self.start_session()
            
            # Dispense H1
            self.dispense(code="H1")
            
            # Wait for the specified interval before next dispense
            time.sleep(self.service_interval)
        
        # This will only be reached when stop_service_routine is called