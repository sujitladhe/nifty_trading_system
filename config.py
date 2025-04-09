# config.py
# Configuration settings for the Nifty trading system

# Angel One SmartAPI credentials
API_KEY = ""          # Your Angel One API key
CLIENT_ID = ""      # Your Angel One client ID
PASSWORD = ""        # Your Angel One password
TOTP_SECRET = ""  # Your TOTP secret for 2FA (if applicable)

# WebSocket and trading parameters
NIFTY_TOKEN = "99926000"               # Angel One token for Nifty 50 (LTP feed)
TRADING_HOURS_START = "09:15"          # IST, market open time
TRADING_HOURS_END = "15:30"            # IST, market close time
LOT_SIZE = 75                          # Nifty options lot size (as of 2025, confirm with broker)
MA_PERIOD = 20                         # Period for Moving Average
BUFFER_CANDLES = 50                    # Number of candles to keep in memory
CSV_FILE = "nifty_candles.csv"         # File to store 1-min candle data

# Risk management
RISK_REWARD_RATIO = 3                  # Take-profit is 3x stop-loss

# Optional: Logging configuration (uncomment if you want logging)
# LOG_FILE = "logs/trade_log.log"
# LOG_LEVEL = "INFO"