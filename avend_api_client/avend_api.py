import requests

class AvendAPI:
    def __init__(self, host="127.0.0.1", port=8080):
        self.base_url = f"http://{host}:{port}/avend"
        self.session = requests.Session()  # Keeps cookie between calls

    def start_session(self):
        params = {"action": "start"}
        try:
            response = self.session.get(self.base_url, params=params)
            return self._format_response(response)
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def dispense(self, code=None):
        params = {"action": "dispense"}
        if code:
            params["code"] = code
        try:
            response = self.session.get(self.base_url, params=params)
            return self._format_response(response)
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def get_info(self):
        url = f"{self.base_url}/info"
        try:
            response = self.session.get(url)
            return self._format_response(response)
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def add_to_cart(self, code):
        return self._post("/cart/add", {"code": code})

    def remove_from_cart(self, code):
        return self._post("/cart/remove", {"code": code})

    def clear_cart(self):
        return self._post("/cart/clear", {})

    def _post(self, path, json_data):
        url = f"{self.base_url}{path}"
        try:
            response = self.session.post(url, json=json_data)
            return self._format_response(response)
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def _format_response(self, response):
        try:
            return {
                "success": response.ok,
                "status_code": response.status_code,
                "response": response.json() if response.content else {}
            }
        except ValueError:
            return {
                "success": response.ok,
                "status_code": response.status_code,
                "response": response.text
            }