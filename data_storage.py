# data_storage.py
import pandas as pd
from datetime import datetime

class DataStorage:
    def __init__(self):
        # Initialize empty DataFrame with candle columns
        self.candles = pd.DataFrame(columns=['Timestamp', 'Open', 'High', 'Low', 'Close'])
        self.current_candle = None
        self.last_minute = None
        # Load previous candles from CSV if it exists
        self.load_previous_candles()

    def load_previous_candles(self):
        """Load historical candles from nifty_candles.csv at startup"""
        csv_file = 'nifty_candles.csv'
        try:
            if pd.io.common.file_exists(csv_file):
                # Read CSV, ensure Timestamp is datetime
                df = pd.read_csv(csv_file)
                if 'Timestamp' not in df.columns:
                    print(f"Warning: {csv_file} missing 'Timestamp' column - starting fresh")
                    return
                df['Timestamp'] = pd.to_datetime(df['Timestamp'])
                # Keep only the last 50 candles (BUFFER_CANDLES) as a copy
                self.candles = df.tail(50).copy()
                # Recalculate MA_20 if enough data
                if len(self.candles) >= 20:
                    self.candles.loc[:, 'MA_20'] = self.candles['Close'].rolling(window=20, min_periods=20).mean()
                print(f"Loaded {len(self.candles)} previous candles from {csv_file}")
            else:
                print(f"No {csv_file} found - starting fresh")
        except Exception as e:
            print(f"Error loading {csv_file}: {e} - starting fresh")
            self.candles = pd.DataFrame(columns=['Timestamp', 'Open', 'High', 'Low', 'Close'])

    def update(self, ltp, timestamp):
        """Update storage with new LTP data"""
        ltp = float(ltp)  # Ensure float for consistency
        if timestamp is not None:
            # Convert UTC timestamp (ms) to IST (+5.5 hours = 19,800,000 ms)
            ist_timestamp = timestamp + 19800000
            current_time = pd.to_datetime(ist_timestamp, unit='ms')
        else:
            current_time = datetime.now()
        current_minute = current_time.replace(second=0, microsecond=0)

        if self.last_minute != current_minute:
            if self.current_candle is not None:
                candle_df = pd.DataFrame([self.current_candle], columns=['Timestamp', 'Open', 'High', 'Low', 'Close'])
                self.candles = pd.concat([self.candles, candle_df], ignore_index=True)
                if len(self.candles) > 50:
                    self.candles = self.candles.iloc[-50:].copy()  # Keep last 50, ensure copy
                self.save_to_csv(candle_df)

            self.current_candle = {
                'Timestamp': current_minute,
                'Open': ltp,
                'High': ltp,
                'Low': ltp,
                'Close': ltp
            }
            self.last_minute = current_minute
        else:
            self.current_candle['High'] = max(self.current_candle['High'], ltp)
            self.current_candle['Low'] = min(self.current_candle['Low'], ltp)
            self.current_candle['Close'] = ltp

        if len(self.candles) >= 20:
            self.candles.loc[:, 'MA_20'] = self.candles['Close'].rolling(window=20, min_periods=20).mean()

    def save_to_csv(self, candle_df):
        """Save new candle to CSV"""
        try:
            header = not pd.io.common.file_exists('nifty_candles.csv')
            candle_df.to_csv('nifty_candles.csv', mode='a', header=header, index=False)
        except Exception as e:
            print(f"Error saving to nifty_candles.csv: {e}")

    def get_candles(self):
        """Return the stored candles"""
        return self.candles

    def get_current_candle(self):
        """Return the current in-progress candle"""
        return self.current_candle

if __name__ == "__main__":
    storage = DataStorage()
    storage.update(22389.3, 1744091640000)
    print(storage.get_current_candle())