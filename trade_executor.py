# trade_executor.py
# Logs paper trades instead of executing real orders

from config import LOT_SIZE, NIFTY_TOKEN
import time
import pandas as pd
import os
import urllib.request
import json

class TradeExecutor:
    def __init__(self, data_fetcher):
        self.data_fetcher = data_fetcher
        self.active_trade = None
        self.log_file = "paper_trades.log"

    def log_trade(self, message):
        """Log trade details to file with timestamp"""
        with open(self.log_file, 'a') as f:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")

    def fetch_instrument_list(self):
        """Fetch and cache Angel One's instrument list if not available locally"""
        instrument_file = "instrument_list.csv"
        
        if not os.path.exists(instrument_file):
            url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            try:
                print("Downloading instrument list...")
                response = urllib.request.urlopen(url)
                instrument_data = json.loads(response.read().decode())
                instrument_df = pd.DataFrame(instrument_data)
                instrument_df.to_csv(instrument_file, index=False)
                print(f"Instrument list saved to {instrument_file}")
            except Exception as e:
                print(f"Failed to fetch instrument list: {e}")
                return None
        
        return pd.read_csv(instrument_file, dtype={'token': str}, low_memory=False)

    def get_symbol_token(self, trading_symbol):
        """Fetch symbol token for the given trading symbol"""
        instrument_df = self.fetch_instrument_list()
        if instrument_df is None:
            raise Exception("Instrument list unavailable")
        
        match = instrument_df[
            (instrument_df['symbol'] == trading_symbol) &
            (instrument_df['exch_seg'] == 'NFO')
        ]
        
        if not match.empty:
            return str(match['token'].iloc[0])
        else:
            raise Exception(f"Token not found for {trading_symbol}")

    def get_atm_strike(self, ltp):
        """Calculate ATM strike based on LTP"""
        strike_interval = 50
        atm_strike = round(ltp / strike_interval) * strike_interval
        return atm_strike

    def place_order(self, signal, ltp):
        """Log a paper trade instead of placing a real order"""
        atm_strike = self.get_atm_strike(ltp)
        symbol = "NIFTY"
        expiry = "10APR"  # Update to current weekly expiry (e.g., April 10, 2025)
        option_type = "CE" if signal['type'] == 'buy' else "PE"
        trading_symbol = f"{symbol}{expiry}{atm_strike}{option_type}"

        trade_details = {
            'type': signal['type'],
            'entry_price': ltp,
            'stop_loss': signal['sl'],
            'take_profit': signal['tp'],
            'symbol': trading_symbol,
            'quantity': LOT_SIZE
        }
        self.active_trade = trade_details
        self.log_trade(f"Paper Trade Entry - {signal['type'].upper()} {trading_symbol} | Entry: {ltp} | SL: {signal['sl']} | TP: {signal['tp']}")
        print(f"Paper Trade initiated: {trade_details}")
        return True

    def monitor_trade(self, ltp):
        """Monitor LTP and log exit if SL or TP is hit"""
        if not self.active_trade:
            return None

        trade_type = self.active_trade['type']
        current_price = ltp

        if trade_type == 'buy':
            if current_price <= self.active_trade['stop_loss']:
                profit = self.active_trade['stop_loss'] - self.active_trade['entry_price']
                self.log_exit("STOPLOSS", profit)
                return {'type': 'exit', 'exit': self.active_trade['stop_loss'], 'profit': profit}
            elif current_price >= self.active_trade['take_profit']:
                profit = self.active_trade['take_profit'] - self.active_trade['entry_price']
                self.log_exit("TAKEPROFIT", profit)
                return {'type': 'exit', 'exit': self.active_trade['take_profit'], 'profit': profit}
        elif trade_type == 'sell':
            if current_price >= self.active_trade['stop_loss']:
                profit = self.active_trade['entry_price'] - self.active_trade['stop_loss']
                self.log_exit("STOPLOSS", profit)
                return {'type': 'exit', 'exit': self.active_trade['stop_loss'], 'profit': profit}
            elif current_price <= self.active_trade['take_profit']:
                profit = self.active_trade['entry_price'] - self.active_trade['take_profit']
                self.log_exit("TAKEPROFIT", profit)
                return {'type': 'exit', 'exit': self.active_trade['take_profit'], 'profit': profit}
        return None

    def log_exit(self, reason, profit):
        """Log the exit of a paper trade"""
        if self.active_trade:
            message = f"Paper Trade Exit - {self.active_trade['symbol']} | Reason: {reason} | Exit: {self.active_trade['stop_loss' if reason == 'STOPLOSS' else 'take_profit']} | Profit: {profit:.2f} points"
            self.log_trade(message)
            print(message)
            self.active_trade = None

# Example usage
if __name__ == "__main__":
    from data_fetcher import DataFetcher
    def dummy_callback(ltp, timestamp):
        print(f"LTP: {ltp}, Timestamp: {timestamp}")
    
    fetcher = DataFetcher(dummy_callback)
    executor = TradeExecutor(fetcher)
    signal = {'type': 'buy', 'entry': 22300, 'sl': 22250, 'tp': 22450}
    executor.place_order(signal, 22300)
    time.sleep(1)
    exit_signal = executor.monitor_trade(22460)
    print("Exit:", exit_signal)