# AVend Mock Server

A Flask-based mock server that simulates the AVend Local Dispense API for testing purposes.

## Features

- Simulates all AVend API endpoints
- Maintains session state and cart functionality
- Provides a web interface to monitor server status
- Logs all API requests for debugging

## Requirements

- Flask

## Usage

1. Start the mock server:

```bash
python Avend_Server_Mock.py
```

1. The server will run on [http://127.0.0.1:8080](http://127.0.0.1:8080) as well as a IP specifed by your network.

2. You can view the server status and active sessions by visiting [http://127.0.0.1:8080](http://127.0.0.1:8080) in your web browser

3. Configure your AVend API client to connect to this mock server instead of the real AVend middleware

## API Endpoints

The mock server implements all the endpoints from the AVend Local Dispense API:

- **Start Session**: `GET /avend?action=start`
- **Dispense Item**: `GET /avend?action=dispense&code=37`
- **Add to Cart**: `GET /avend?action=add&code=24`
- **Remove from Cart**: `GET /avend?action=remove&code=24`
- **Clear Cart**: `GET /avend?action=clear`
- **Dispense Cart**: `GET /avend?action=dispense`
- **Get Info**: `GET /avend?action=info`

## Testing

You can test the mock server using curl or any HTTP client:

```bash
# Start a session
curl http://127.0.0.1:8080/avend?action=start

# Add an item to the cart
curl http://127.0.0.1:8080/avend?action=add&code=24

# Dispense the cart
curl http://127.0.0.1:8080/avend?action=dispense
```

## Notes

- Sessions expire after 5 minutes of inactivity, just like in the real AVend middleware
- The mock server simulates the behavior of the real AVend API but doesn't actually control any hardware
- All responses are returned as JSON for GUI formatting.
