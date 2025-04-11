# trade_executor.py
# Logs paper trades instead of executing real orders

import requests
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
        self.telegram_bot_token = '7304000359:AAFkzdTKOFkoI1ucgWXZ-rH4fYB8cnWbQhc'  # Replace with your token
        self.telegram_chat_id = '669766342'     # Replace with your cha

    def send_telegram_message(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        payload = {'chat_id': self.telegram_chat_id, 'text': message}
        requests.post(url, data=payload)

    def log_trade(self, message):
        """Log trade details to file with timestamp"""
        with open(self.log_file, 'a') as f:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
            self.send_telegram_message(message)  # Send to Telegram
            
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
        expiry = "10APR"  # Hardcoded for now—update dynamically for April 17, 2025, etc.
        option_type = "CE" if signal['type'] == 'buy' else "PE"
        trading_symbol = f"{symbol}{expiry}{atm_strike}{option_type}"

        trade_details = {
            'type': signal['type'],
            'entry_price': float(ltp),  # Ensure float for consistency
            'stop_loss': float(signal['sl']),
            'take_profit': float(signal['tp']),
            'symbol': trading_symbol,
            'quantity': LOT_SIZE
        }
        self.active_trade = trade_details
        self.log_trade(f"Paper Trade Entry - {signal['type'].upper()} {trading_symbol} | Entry: {ltp} | SL: {signal['sl']} | TP: {signal['tp']}")
        print(f"Paper Trade initiated: {trade_details}")
        return True

    def monitor_trade(self, ltp):
        """Monitor LTP and log exit if SL or TP is hit"""
        if self.active_trade is None:
            return None  # No active trade to monitor

        trade_type = self.active_trade['type']
        current_price = float(ltp)  # Ensure float
        entry = self.active_trade['entry_price']
        sl = self.active_trade['stop_loss']
        tp = self.active_trade['take_profit']
        symbol = self.active_trade['symbol']

        if trade_type == 'buy':
            profit = current_price - entry
            if current_price <= sl:
                self.log_exit("STOPLOSS", profit)
                return {'type': 'exit', 'exit': sl, 'profit': profit}
            elif current_price >= tp:
                self.log_exit("TAKEPROFIT", profit)
                return {'type': 'exit', 'exit': tp, 'profit': profit}
        elif trade_type == 'sell':
            profit = entry - current_price  # Fixed: Correct sell profit calc
            if current_price >= sl:
                self.log_exit("STOPLOSS", profit)
                return {'type': 'exit', 'exit': sl, 'profit': profit}
            elif current_price <= tp:
                self.log_exit("TAKEPROFIT", profit)
                return {'type': 'exit', 'exit': tp, 'profit': profit}
        return None

    def log_exit(self, reason, profit):
        """Log the exit of a paper trade"""
        if self.active_trade:
            exit_price = self.active_trade['stop_loss'] if reason == 'STOPLOSS' else self.active_trade['take_profit']
            message = f"Paper Trade Exit - {self.active_trade['symbol']} | Reason: {reason} | Exit: {exit_price} | Profit: {profit:.2f} points"
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