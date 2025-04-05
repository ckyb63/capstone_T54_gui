"""
Test Mock Avend Server
Max Chen - v0.3.0
"""

from flask import Flask, request, jsonify
import time
import logging
import uuid

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Store active sessions and carts
sessions = {}

class Session:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.created_at = time.time()
        self.cart = []
        self.last_activity = time.time()
    
    def is_expired(self):
        # Sessions expire after 5 minutes of inactivity
        return (time.time() - self.last_activity) > 300
    
    def update_activity(self):
        self.last_activity = time.time()
    
    def add_to_cart(self, code):
        self.cart.append(code)
        self.update_activity()
    
    def remove_from_cart(self, code):
        if code in self.cart:
            self.cart.remove(code)
            self.update_activity()
            return True
        return False
    
    def clear_cart(self):
        self.cart = []
        self.update_activity()


def get_active_session():
    """Get the active session or None if no active session exists"""
    # Clean up expired sessions
    expired_sessions = [sid for sid, session in sessions.items() if session.is_expired()]
    for sid in expired_sessions:
        logger.info(f"Session {sid} expired and removed")
        del sessions[sid]
    
    # Return the first non-expired session if any
    active_sessions = [session for session in sessions.values() if not session.is_expired()]
    return active_sessions[0] if active_sessions else None


@app.route('/avend', methods=['GET'])
def avend_api():
    """Handle AVend API requests"""
    action = request.args.get('action')
    code = request.args.get('code')
    mode = request.args.get('mode', 'double')
    
    logger.info(f"Received request: action={action}, code={code}, mode={mode}")
    
    # Process the action
    if action == 'start':
        # Create a new session
        session = Session()
        sessions[session.id] = session
        logger.info(f"Started new session: {session.id}")
        return jsonify({"status": "success", "message": "Session started", "session_id": session.id})
    
    # All other actions require an active session
    session = get_active_session()
    if not session and action != 'info':
        logger.warning("No active session found")
        return jsonify({"status": "error", "message": "No active session. Call 'start' first."}), 400
    
    # Handle other actions
    if action == 'dispense':
        if code:
            # Single item dispense
            logger.info(f"Dispensing item: {code} (mode: {mode})")
            
            # If mode is 'double' and code is a single digit, pad it with a leading zero
            if mode == 'double' and len(str(code)) == 1:
                code = f"0{code}"
                logger.info(f"Padded code to: {code}")
            
            return jsonify({
                "status": "success", 
                "message": f"Dispensed item: {code}",
                "item": code
            })
        elif session and session.cart:
            # Cart dispense
            items = session.cart.copy()
            session.clear_cart()
            logger.info(f"Dispensing cart items: {items}")
            return jsonify({
                "status": "success", 
                "message": f"Dispensed {len(items)} items from cart",
                "items": items
            })
        else:
            logger.warning("Nothing to dispense (empty cart and no code provided)")
            return jsonify({"status": "error", "message": "Nothing to dispense"}), 400
    
    elif action == 'add' and code:
        session.add_to_cart(code)
        logger.info(f"Added item to cart: {code}")
        return jsonify({
            "status": "success", 
            "message": f"Added item to cart: {code}",
            "cart": session.cart
        })
    
    elif action == 'remove' and code:
        if session.remove_from_cart(code):
            logger.info(f"Removed item from cart: {code}")
            return jsonify({
                "status": "success", 
                "message": f"Removed item from cart: {code}",
                "cart": session.cart
            })
        else:
            logger.warning(f"Item not found in cart: {code}")
            return jsonify({"status": "error", "message": f"Item not found in cart: {code}"}), 400
    
    elif action == 'clear':
        session.clear_cart()
        logger.info("Cleared cart")
        return jsonify({"status": "success", "message": "Cart cleared"})
    
    elif action == 'info':
        # Return information about the mock server
        return jsonify({
            "status": "success",
            "server": "AVend Mock Server",
            "version": "1.0.0",
            "active_sessions": len([s for s in sessions.values() if not s.is_expired()]),
            "total_sessions": len(sessions)
        })
    
    else:
        logger.warning(f"Invalid action or missing required parameters: {action}")
        return jsonify({"status": "error", "message": "Invalid action or missing required parameters"}), 400


@app.route('/')
def index():
    """Return a simple HTML page with information about the mock server"""
    active_session = get_active_session()
    active_sessions_count = len([s for s in sessions.values() if not s.is_expired()])
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AVend Mock Server</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
            h1 {{ color: #333; }}
            h2 {{ color: #555; }}
            pre {{ background-color: #f5f5f5; padding: 10px; border-radius: 5px; }}
            .endpoint {{ background-color: #e9f7fe; padding: 10px; margin: 10px 0; border-radius: 5px; }}
            .cart-item {{ background-color: #f0f0f0; padding: 5px; margin: 2px; display: inline-block; border-radius: 3px; }}
        </style>
    </head>
    <body>
        <h1>AVend Mock Server</h1>
        <p>This is a mock server that simulates the AVend Local Dispense API.</p>
        
        <h2>Server Status</h2>
        <p>Active Sessions: {active_sessions_count}</p>
    """
    
    if active_session:
        created_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(active_session.created_at))
        last_activity_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(active_session.last_activity))
        cart_empty_text = 'None' if not active_session.cart else ''
        
        html += f"""
        <h2>Current Active Session</h2>
        <p>Session ID: {active_session.id}</p>
        <p>Created: {created_time}</p>
        <p>Last Activity: {last_activity_time}</p>
        <p>Cart Items: {cart_empty_text}</p>
        """
        
        if active_session.cart:
            html += "<div>"
            for item in active_session.cart:
                html += f'<span class="cart-item">{item}</span>'
            html += "</div>"
    
    html += """
        <h2>API Endpoints</h2>
        <div class="endpoint">
            <h3>Start Session</h3>
            <pre>GET /avend?action=start</pre>
        </div>
        
        <div class="endpoint">
            <h3>Dispense Item</h3>
            <pre>GET /avend?action=dispense&code=37</pre>
        </div>
        
        <div class="endpoint">
            <h3>Add to Cart</h3>
            <pre>GET /avend?action=add&code=24</pre>
        </div>
        
        <div class="endpoint">
            <h3>Remove from Cart</h3>
            <pre>GET /avend?action=remove&code=24</pre>
        </div>
        
        <div class="endpoint">
            <h3>Clear Cart</h3>
            <pre>GET /avend?action=clear</pre>
        </div>
        
        <div class="endpoint">
            <h3>Dispense Cart</h3>
            <pre>GET /avend?action=dispense</pre>
        </div>
        
        <div class="endpoint">
            <h3>Get Info</h3>
            <pre>GET /avend?action=info</pre>
        </div>
    </body>
    </html>
    """
    
    return html


if __name__ == '__main__':
    logger.info("Starting AVend Mock Server on http://127.0.0.1:8080")
    app.run(host='0.0.0.0', port=8080, debug=True)
    # Setting up on another laptop, note down the IPv4 address using `ipconfig` or `ifconfig`
