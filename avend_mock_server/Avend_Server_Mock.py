# Avend Mock Server to simulate the Avend Vending Machine kit.
# Max Chen

import time
import datetime
import logging
import uuid
from collections import deque
from flask import Flask, request, jsonify, make_response

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Global variables
sessions = {}  # Dictionary to store active sessions
request_history = deque(maxlen=50)  # Store the last 50 requests

# Session timeout in seconds (5 minutes)
SESSION_TIMEOUT = 300

class Session:
    """Class to represent a session with the AVend API"""
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.created_at = time.time()
        self.last_activity = time.time()
        self.cart = []
    
    def update_activity(self):
        """Update the last activity time"""
        self.last_activity = time.time()
    
    def is_expired(self):
        """Check if the session has expired"""
        return (time.time() - self.last_activity) > SESSION_TIMEOUT
    
    def add_to_cart(self, code):
        """Add an item to the cart"""
        if code not in self.cart:
            self.cart.append(code)
        self.update_activity()
    
    def clear_cart(self):
        """Clear the cart"""
        self.cart = []
        self.update_activity()

def get_active_session():
    """Get the most recently active non-expired session"""
    active_sessions = [s for s in sessions.values() if not s.is_expired()]
    if active_sessions:
        # Sort by last activity time (most recent first)
        return sorted(active_sessions, key=lambda s: s.last_activity, reverse=True)[0]
    return None

def create_session():
    """Create a new session"""
    session = Session()
    sessions[session.id] = session
    return session

@app.route('/avend', methods=['GET'])
def avend_api():
    action = request.args.get('action')
    code = request.args.get('code')
    
    # Log the request
    client_ip = request.remote_addr
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    request_data = {
        'timestamp': timestamp,
        'client_ip': client_ip,
        'action': action,
        'code': code,
        'args': dict(request.args)
    }
    request_history.appendleft(request_data)
    logger.info(f"Request: {action}, Code: {code}, IP: {client_ip}")
    
    if action == 'start':
        # Create a new session
        session = create_session()
        logger.info(f"New session created: {session.id}")
        
        # Set a cookie with the session ID and redirect to dashboard
        response = make_response("")
        response.set_cookie('session_id', session.id)
        response.headers['Location'] = '/'
        response.status_code = 302
        return response
    
    elif action == 'dispense':
        if not code:
            logger.warning("Dispense action called without a code")
            return jsonify({"status": "error", "message": "Code is required for dispense action"}), 400
        
        # Get or create session
        session_id = request.cookies.get('session_id')
        if session_id and session_id in sessions and not sessions[session_id].is_expired():
            session = sessions[session_id]
        else:
            session = create_session()
        
        session.update_activity()
        logger.info(f"Dispensing item: {code}, Session: {session.id}")
        
        # Set a cookie with the session ID and redirect to dashboard
        response = make_response("")
        response.set_cookie('session_id', session.id)
        response.headers['Location'] = '/'
        response.status_code = 302
        return response
    
    elif action == 'add_to_cart':
        if not code:
            logger.warning("Add to cart action called without a code")
            return jsonify({"status": "error", "message": "Code is required for add_to_cart action"}), 400
        
        # Get or create session
        session_id = request.cookies.get('session_id')
        if session_id and session_id in sessions and not sessions[session_id].is_expired():
            session = sessions[session_id]
        else:
            session = create_session()
        
        session.add_to_cart(code)
        logger.info(f"Added to cart: {code}, Session: {session.id}, Cart: {session.cart}")
        
        # Set a cookie with the session ID and redirect to dashboard
        response = make_response("")
        response.set_cookie('session_id', session.id)
        response.headers['Location'] = '/'
        response.status_code = 302
        return response
    
    elif action == 'dispense_cart':
        # Get or create session
        session_id = request.cookies.get('session_id')
        if session_id and session_id in sessions and not sessions[session_id].is_expired():
            session = sessions[session_id]
        else:
            session = create_session()
        
        if not session.cart:
            logger.warning(f"Dispense cart called with empty cart, Session: {session.id}")
            return jsonify({"status": "error", "message": "Cart is empty"}), 400
        
        cart_items = session.cart.copy()
        session.clear_cart()
        logger.info(f"Dispensing cart: {cart_items}, Session: {session.id}")
        
        # Set a cookie with the session ID and redirect to dashboard
        response = make_response("")
        response.set_cookie('session_id', session.id)
        response.headers['Location'] = '/'
        response.status_code = 302
        return response
    
    elif action == 'clear_cart':
        # Get session
        session_id = request.cookies.get('session_id')
        if not session_id or session_id not in sessions or sessions[session_id].is_expired():
            logger.warning("Clear cart called without a valid session")
            return jsonify({"status": "error", "message": "No active session"}), 400
        
        session = sessions[session_id]
        session.clear_cart()
        logger.info(f"Cart cleared, Session: {session.id}")
        
        # Redirect to dashboard
        response = make_response("")
        response.headers['Location'] = '/'
        response.status_code = 302
        return response
    
    else:
        logger.warning(f"Invalid action or missing required parameters: {action}")
        return jsonify({"status": "error", "message": "Invalid action or missing required parameters"}), 400


@app.route('/')
def index():
    """Return a simple HTML page with information about the mock server"""
    active_session = get_active_session()
    active_sessions_count = len([s for s in sessions.values() if not s.is_expired()])
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AVend Mock Server</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script>
            // Use AJAX for real-time updates instead of page refresh
            function updateDashboard() {
                // Update server time
                const timeElement = document.getElementById('server-time');
                const dateElement = document.getElementById('server-date');
                if (timeElement && dateElement) {
                    const now = new Date();
                    timeElement.textContent = now.toTimeString().split(' ')[0];
                    dateElement.textContent = now.toISOString().split('T')[0];
                }
                
                // Fetch updated data
                fetch('/dashboard-data')
                    .then(response => response.json())
                    .then(data => {
                        // Update active sessions count
                        const sessionsElement = document.getElementById('active-sessions');
                        if (sessionsElement) {
                            sessionsElement.textContent = data.active_sessions_count;
                        }
                        
                        // Update session info if available
                        if (data.active_session) {
                            document.getElementById('session-container').innerHTML = data.active_session_html;
                        }
                        
                        // Update request history
                        document.getElementById('request-history').innerHTML = data.request_history_html;
                        
                        // Update server stats
                        if (data.server_stats_html) {
                            document.getElementById('server-stats').innerHTML = data.server_stats_html;
                        }
                    })
                    .catch(error => console.error('Error updating dashboard:', error));
            }
            
            // Update every 2 seconds
            document.addEventListener('DOMContentLoaded', function() {
                // Initial update
                updateDashboard();
                // Set interval for continuous updates
                setInterval(updateDashboard, 1000);
            });
        </script>
        <style>
            :root {
                --primary-color: #007AFF;
                --secondary-color: #FF9500;
                --success-color: #4CAF50;
                --error-color: #FF3B30;
                --background-color: #f8f9fa;
                --card-background: white;
                --text-color: #333;
                --border-color: #e0e0e0;
            }
            
            * { box-sizing: border-box; }
            
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                margin: 0; 
                padding: 0; 
                background-color: var(--background-color); 
                color: var(--text-color);
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            
            .header {
                background-color: var(--primary-color);
                color: white;
                padding: 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-radius: 8px;
                margin-bottom: 20px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            
            .header h1 {
                margin: 0;
                font-size: 24px;
            }
            
            .auto-refresh {
                color: rgba(255,255,255,0.8);
                font-size: 0.8em;
            }
            
            .dashboard {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }
            
            .card {
                background-color: var(--card-background);
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            
            .card h2 {
                margin-top: 0;
                color: var(--primary-color);
                font-size: 18px;
                border-bottom: 1px solid var(--border-color);
                padding-bottom: 10px;
            }
            
            .card-content {
                padding: 10px 0;
            }
            
            .stat {
                display: flex;
                align-items: center;
                margin-bottom: 10px;
            }
            
            .stat-label {
                flex: 1;
                color: #666;
            }
            
            .stat-value {
                font-weight: bold;
                font-size: 18px;
            }
            
            .session-info {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 15px;
            }
            
            .cart-items {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin-top: 15px;
            }
            
            .cart-item {
                background-color: var(--primary-color);
                color: white;
                padding: 5px 10px;
                border-radius: 5px;
                font-size: 0.9em;
            }
            
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
                font-size: 0.9em;
            }
            
            th, td {
                padding: 12px 15px;
                text-align: left;
                border-bottom: 1px solid var(--border-color);
            }
            
            th {
                background-color: #f2f2f2;
                font-weight: 600;
            }
            
            tr:last-child td {
                border-bottom: none;
            }
            
            tr:hover {
                background-color: #f5f5f5;
            }
            
            .timestamp {
                white-space: nowrap;
                font-size: 0.9em;
                color: #666;
            }
            
            .action {
                font-weight: 600;
            }
            
            .success {
                color: var(--success-color);
            }
            
            .error {
                color: var(--error-color);
            }
            
            .api-section {
                margin-top: 30px;
            }
            
            .endpoints {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
                margin-top: 15px;
            }
            
            .endpoint {
                background-color: white;
                border-radius: 8px;
                padding: 15px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            
            .endpoint h3 {
                margin-top: 0;
                color: var(--primary-color);
                font-size: 16px;
            }
            
            pre {
                background-color: #f5f5f5;
                padding: 10px;
                border-radius: 5px;
                overflow-x: auto;
                font-size: 0.9em;
            }
            
            .btn {
                display: inline-block;
                background-color: var(--primary-color);
                color: white;
                padding: 8px 15px;
                border-radius: 5px;
                text-decoration: none;
                font-size: 0.9em;
                margin-top: 10px;
            }
            
            .btn:hover {
                background-color: #0056b3;
            }
            
            .btn-danger {
                background-color: var(--error-color);
            }
            
            .btn-danger:hover {
                background-color: #c82333;
            }
            
            @media (max-width: 768px) {
                .dashboard {
                    grid-template-columns: 1fr;
                }
                
                .endpoints {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>AVend Mock Server</h1>
            <span class="auto-refresh">Real-time updates</span>
        </div>
        
        <div class="container">
    """
    
    # Add dashboard container
    html += """
            <div class="dashboard">
    """
    
    # Add server stats section with ID for updates
    html += """
                <div id="server-stats">
    """
    
    # Add server stats card with dynamic content
    html += f"""
                    <div class="card">
                        <h2>Server Status</h2>
                        <div class="card-content">
                            <div class="session-info">
                                <div class="stat">
                                    <div class="stat-label">Active Sessions:</div>
                                    <div class="stat-value" id="active-sessions">{active_sessions_count}</div>
                                </div>
                                <div class="stat">
                                    <div class="stat-label">Server Time:</div>
                                    <div class="stat-value" id="server-time">{datetime.datetime.now().strftime('%H:%M:%S')}</div>
                                </div>
                                <div class="stat">
                                    <div class="stat-label">Date:</div>
                                    <div class="stat-value" id="server-date">{datetime.datetime.now().strftime('%Y-%m-%d')}</div>
                                </div>
                                <a href="/clear-history" class="btn btn-danger">Clear Request History</a>
                            </div>
                        </div>
                    </div>
                </div>
    """
    
    # Add session container for active session info
    html += """
                <div id="session-container">
    """
    
    if active_session:
        created_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(active_session.created_at))
        last_activity_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(active_session.last_activity))
        cart_empty_text = 'None' if not active_session.cart else ''
        
        html += f"""
                    <div class="card">
                        <h2>Active Session</h2>
                        <div class="card-content">
                            <div class="session-info">
                                <div class="stat">
                                    <div class="stat-label">Session ID:</div>
                                    <div class="stat-value" style="font-size: 14px; word-break: break-all;">{active_session.id}</div>
                                </div>
                                <div class="stat">
                                    <div class="stat-label">Created:</div>
                                    <div class="stat-value" style="font-size: 14px;">{created_time}</div>
                                </div>
                                <div class="stat">
                                    <div class="stat-label">Last Activity:</div>
                                    <div class="stat-value" style="font-size: 14px;">{last_activity_time}</div>
                                </div>
                                <div class="stat">
                                    <div class="stat-label">Cart Items:</div>
                                    <div class="stat-value">{len(active_session.cart) if active_session.cart else 0}</div>
                                </div>
                            </div>
        """
        
        if active_session.cart:
            html += """
                            <div class="cart-items">
            """
            for item in active_session.cart:
                html += f'<span class="cart-item">{item}</span>'
            
            html += """
                            </div>
            """
            
        html += """
                        </div>
                    </div>
        """
    else:
        html += """
                    <div class="card">
                        <h2>Active Session</h2>
                        <div class="card-content">
                            <p>No active session. Start a new session to begin.</p>
                            <a href="/avend?action=start" class="btn">Start New Session</a>
                        </div>
                    </div>
        """
        
    html += """
                </div>
            </div>
    """
    
    # Add request history section with ID for updates
    html += """
            <div class="card">
                <h2>Request History</h2>
                <div class="card-content" id="request-history">
                    <table>
                        <tr>
                            <th>Time</th>
                            <th>Client IP</th>
                            <th>Action</th>
                            <th>Code</th>
                            <th>Details</th>
                        </tr>
    """
    
    # Add each request to the table
    if request_history:
        for req in request_history:
            action = req.get('action', '-')
            code = req.get('code', '-')
            timestamp = req.get('timestamp', '-')
            client_ip = req.get('client_ip', '-')
            args = req.get('args', {})
            
            # Format args as a string, excluding action and code which are already displayed
            args_str = ', '.join([f"{k}={v}" for k, v in args.items() if k not in ['action', 'code']])
            if args_str:
                details = args_str
            else:
                details = '-'
            
            html += f"""
                        <tr>
                            <td class="timestamp">{timestamp}</td>
                            <td>{client_ip}</td>
                            <td class="action">{action}</td>
                            <td>{code}</td>
                            <td>{details}</td>
                        </tr>
            """
    else:
        html += """
                        <tr>
                            <td colspan="5" style="text-align: center;">No requests received yet</td>
                        </tr>
        """
    
    html += """
                    </table>
                </div>
            </div>
    """
    
    # Add API documentation section
    html += """
            <div class="api-section">
                <h2>API Documentation</h2>
                <div class="endpoints">
                    <div class="endpoint">
                        <h3>Start Session</h3>
                        <p>Start a new session with the AVend API</p>
                        <pre>/avend?action=start</pre>
                        <a href="/avend?action=start" class="btn">Try It</a>
                    </div>
                    
                    <div class="endpoint">
                        <h3>Dispense Item</h3>
                        <p>Dispense an item from the vending machine</p>
                        <pre>/avend?action=dispense&code=A1</pre>
                        <a href="/avend?action=dispense&code=A1" class="btn">Try It</a>
                    </div>
                    
                    <div class="endpoint">
                        <h3>Add to Cart</h3>
                        <p>Add an item to the cart</p>
                        <pre>/avend?action=add_to_cart&code=A1</pre>
                        <a href="/avend?action=add_to_cart&code=A1" class="btn">Try It</a>
                    </div>
                    
                    <div class="endpoint">
                        <h3>Dispense Cart</h3>
                        <p>Dispense all items in the cart</p>
                        <pre>/avend?action=dispense_cart</pre>
                        <a href="/avend?action=dispense_cart" class="btn">Try It</a>
                    </div>
                    
                    <div class="endpoint">
                        <h3>Clear Cart</h3>
                        <p>Clear all items from the cart</p>
                        <pre>/avend?action=clear_cart</pre>
                        <a href="/avend?action=clear_cart" class="btn">Try It</a>
                    </div>
                    
                    <div class="endpoint">
                        <h3>Clear History</h3>
                        <p>Clear the request history</p>
                        <pre>/clear-history</pre>
                        <a href="/clear-history" class="btn btn-danger">Clear History</a>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


@app.route('/dashboard-data', methods=['GET'])
def dashboard_data():
    """Return JSON data for dashboard updates"""
    active_session = get_active_session()
    active_sessions_count = len([s for s in sessions.values() if not s.is_expired()])
    
    # Generate HTML for active session
    active_session_html = ""
    if active_session:
        created_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(active_session.created_at))
        last_activity_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(active_session.last_activity))
        
        active_session_html = f"""
        <div class="card">
            <h2>Active Session</h2>
            <div class="card-content">
                <div class="session-info">
                    <div class="stat">
                        <div class="stat-label">Session ID:</div>
                        <div class="stat-value" style="font-size: 14px; word-break: break-all;">{active_session.id}</div>
                    </div>
                    <div class="stat">
                        <div class="stat-label">Created:</div>
                        <div class="stat-value" style="font-size: 14px;">{created_time}</div>
                    </div>
                    <div class="stat">
                        <div class="stat-label">Last Activity:</div>
                        <div class="stat-value" style="font-size: 14px;">{last_activity_time}</div>
                    </div>
                    <div class="stat">
                        <div class="stat-label">Cart Items:</div>
                        <div class="stat-value">{len(active_session.cart) if active_session.cart else 0}</div>
                    </div>
                </div>
        """
        
        if active_session.cart:
            active_session_html += "<div class=\"cart-items\">"
            for item in active_session.cart:
                active_session_html += f'<span class="cart-item">{item}</span>'
            active_session_html += "</div>"
            
        active_session_html += """
                </div>
            </div>
        """
    else:
        active_session_html = """
        <div class="card">
            <h2>Active Session</h2>
            <div class="card-content">
                <p>No active session. Start a new session to begin.</p>
                <a href="/avend?action=start" class="btn">Start New Session</a>
            </div>
        </div>
        """
    
    # Generate HTML for request history
    request_history_html = """
    <table>
        <tr>
            <th>Time</th>
            <th>Client IP</th>
            <th>Action</th>
            <th>Code</th>
            <th>Details</th>
        </tr>
    """
    
    if request_history:
        for req in request_history:
            action = req.get('action', '-')
            code = req.get('code', '-')
            timestamp = req.get('timestamp', '-')
            client_ip = req.get('client_ip', '-')
            args = req.get('args', {})
            
            # Format args as a string, excluding action and code which are already displayed
            args_str = ', '.join([f"{k}={v}" for k, v in args.items() if k not in ['action', 'code']])
            if args_str:
                details = args_str
            else:
                details = '-'
            
            request_history_html += f"""
            <tr>
                <td class="timestamp">{timestamp}</td>
                <td>{client_ip}</td>
                <td class="action">{action}</td>
                <td>{code}</td>
                <td>{details}</td>
            </tr>
            """
    else:
        request_history_html += """
            <tr>
                <td colspan="5" style="text-align: center;">No requests received yet</td>
            </tr>
        """
    
    request_history_html += "</table>"
    
    # Generate HTML for server stats
    server_stats_html = f"""
        <div class="card">
            <h2>Server Status</h2>
            <div class="card-content">
                <div class="session-info">
                    <div class="stat">
                        <div class="stat-label">Active Sessions:</div>
                        <div class="stat-value" id="active-sessions">{active_sessions_count}</div>
                    </div>
                    <div class="stat">
                        <div class="stat-label">Server Time:</div>
                        <div class="stat-value" id="server-time">{datetime.datetime.now().strftime('%H:%M:%S')}</div>
                    </div>
                    <div class="stat">
                        <div class="stat-label">Date:</div>
                        <div class="stat-value" id="server-date">{datetime.datetime.now().strftime('%Y-%m-%d')}</div>
                    </div>
                    <a href="/clear-history" class="btn btn-danger">Clear Request History</a>
                </div>
            </div>
        </div>
    """
    
    return jsonify({
        "active_sessions_count": active_sessions_count,
        "active_session": bool(active_session),
        "active_session_html": active_session_html,
        "request_history_html": request_history_html,
        "server_stats_html": server_stats_html
    })

@app.route('/clear-history', methods=['GET'])
def clear_history():
    """Clear the request history"""
    global request_history
    request_history = deque(maxlen=50)  # Create a new empty deque
    logger.info("Request history cleared via endpoint")
    
    # Redirect to dashboard
    response = make_response("")
    response.headers['Location'] = '/'
    response.status_code = 302
    return response

if __name__ == '__main__':
    # Initialize request history
    logger.info("Request history initialized as empty")
    # Run the app
    app.run(host='0.0.0.0', port=8080, debug=True)
