import requests
from urllib.parse import quote

class AvendAPI:
    """
    Client for the AVend Local Dispense API
    """
    def __init__(self, host="127.0.0.1", port=8080):
        """
        Initialize the AVend API client
        
        Args:
            host (str): IP address or hostname of the AVend middleware
            port (int): TCP port number for the AVend middleware
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/avend"
    
    def start_session(self):
        """
        Start a session to begin transaction
        
        Returns:
            dict: Response from the API
        """
        url = f"{self.base_url}?action=start"
        try:
            response = requests.get(url)
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response": response.text
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def dispense(self, code=None, mode=None):
        """
        Dispense selection or items in cart
        
        Args:
            code (str, optional): Selection code to dispense
            mode (str, optional): 'single' or 'double' for padding behavior
            
        Returns:
            dict: Response from the API
        """
        url = f"{self.base_url}?action=dispense"
        
        if code:
            # Encode special characters like * or #
            encoded_code = quote(str(code))
            url += f"&code={encoded_code}"
        
        if mode and mode in ["single", "double"]:
            url += f"&mode={mode}"
        
        try:
            response = requests.get(url)
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response": response.text
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def add_to_cart(self, code):
        """
        Add selection to cart
        
        Args:
            code (str): Selection code to add
            
        Returns:
            dict: Response from the API
        """
        # Encode special characters like * or #
        encoded_code = quote(str(code))
        url = f"{self.base_url}?action=add&code={encoded_code}"
        
        try:
            response = requests.get(url)
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response": response.text
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def remove_from_cart(self, code):
        """
        Remove selection from cart
        
        Args:
            code (str): Selection code to remove
            
        Returns:
            dict: Response from the API
        """
        # Encode special characters like * or #
        encoded_code = quote(str(code))
        url = f"{self.base_url}?action=remove&code={encoded_code}"
        
        try:
            response = requests.get(url)
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response": response.text
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def clear_cart(self):
        """
        Clear the cart
        
        Returns:
            dict: Response from the API
        """
        url = f"{self.base_url}?action=clear"
        
        try:
            response = requests.get(url)
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response": response.text
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_info(self):
        """
        Get information about the current configuration
        
        Returns:
            dict: Response from the API
        """
        url = f"{self.base_url}?action=info"
        
        try:
            response = requests.get(url)
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response": response.text
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
