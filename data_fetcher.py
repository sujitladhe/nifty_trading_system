# data_fetcher.py
# Fetches real-time Nifty LTP data via Angel One SmartAPI WebSocket V2

from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from SmartApi import SmartConnect
from config import API_KEY, CLIENT_ID, PASSWORD, TOTP_SECRET, NIFTY_TOKEN
import pyotp
import threading

class DataFetcher:
    def __init__(self, on_tick_callback):
        self.on_tick_callback = on_tick_callback  # Callback to pass LTP data
        self.token = NIFTY_TOKEN  # Using config value (e.g., "26000" or "99926000")
        self.auth_token = None
        self.feed_token = None
        self.ws = None
        self.running = False
        self.correlation_id = "nifty_trading_system"

    def authenticate(self):
        """Authenticate with Angel One API to get tokens"""
        client = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = client.generateSession(CLIENT_ID, PASSWORD, totp)
        self.auth_token = data['data']['jwtToken']
        self.feed_token = data['data']['feedToken']
        print("Authenticated successfully. Tokens obtained.")
        
    def on_data(self, wsapp, message):
        """Handle incoming WebSocket messages"""
        # print(f"Raw message: {message}")  # Debug print
        if isinstance(message, dict) and 'last_traded_price' in message:
            ltp = float(message['last_traded_price']) / 100  # Convert paise to INR
            timestamp = message.get('exchange_timestamp', None)
            # print(f"Tick received - LTP: {ltp}, Timestamp: {timestamp}")  # Debug print
            self.on_tick_callback(ltp, timestamp)

    def on_open(self, wsapp):
        """Subscribe to Nifty LTP feed when WebSocket opens"""
        print("WebSocket V2 connection opened.")
        token_list = [{"exchangeType": "1", "tokens": [self.token]}]  # NSE
        self.ws.subscribe(self.correlation_id, 1, token_list)  # Mode 1 = LTP
        # print(f"Subscribed to Nifty token: {self.token}")

    def on_error(self, wsapp, error):
        """Handle WebSocket errors"""
        print(f"WebSocket V2 error: {error}")

    def on_close(self, wsapp):
        """Handle WebSocket closure"""
        print("WebSocket V2 connection closed.")
        self.running = False

    def start(self):
        """Start the WebSocket connection"""
        if not self.auth_token:
            self.authenticate()
        
        self.ws = SmartWebSocketV2(self.auth_token, API_KEY, CLIENT_ID, self.feed_token)
        self.ws.on_open = self.on_open
        self.ws.on_data = self.on_data
        self.ws.on_error = self.on_error
        self.ws.on_close = self.on_close
        
        self.running = True
        print("Starting WebSocket V2 connection...")
        threading.Thread(target=self.ws.connect, daemon=True).start()

    def stop(self):
        """Stop the WebSocket connection"""
        if self.running and self.ws:
            try:
                self.ws.close_connection()  # Correct method for SmartWebSocketV2
            except AttributeError:
                print("Warning: Could not close WebSocket cleanly")
            self.running = False

# Example usage
if __name__ == "__main__":
    def dummy_callback(ltp, timestamp):
        # print(f"LTP: {ltp}, Timestamp: {timestamp}")
        print(f"Program running")
    fetcher = DataFetcher(dummy_callback)
    fetcher.start()
    input("Press Enter to stop...\n")
    fetcher.stop()