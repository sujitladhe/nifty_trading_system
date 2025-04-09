# trade_executor.py
# Executes trades on Angel One platform and manages exits

from SmartApi import SmartConnect
from config import API_KEY, CLIENT_ID, PASSWORD, TOTP_SECRET, LOT_SIZE, NIFTY_TOKEN
import pyotp
import time
import pandas as pd
import os
import urllib.request
import json

class TradeExecutor:
    def __init__(self, data_fetcher):
        self.client = None
        self.data_fetcher = data_fetcher
        self.active_trade = None
        self.authenticated = False

    def authenticate(self):
        """Authenticate with Angel One API"""
        self.client = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        response = self.client.generateSession(CLIENT_ID, PASSWORD, totp)
        if response['status']:
            self.authenticated = True
            print("TradeExecutor authenticated successfully.")
        else:
            raise Exception("Authentication failed: " + response['message'])

    def fetch_instrument_list(self):
        """Fetch and cache Angel One's instrument list if not available locally"""
        instrument_file = "instrument_list.csv"
        
        if not os.path.exists(instrument_file):
            if not self.authenticated:
                self.authenticate()
            
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
        """Place a buy order for ATM CE or PE"""
        if not self.authenticated:
            self.authenticate()

        atm_strike = self.get_atm_strike(ltp)
        symbol = "NIFTY"
        expiry = "25APR"  # Adjust to current weekly expiry
        option_type = "CE" if signal['type'] == 'buy' else "PE"
        trading_symbol = f"{symbol}{expiry}{atm_strike}{option_type}"

        order_params = {
            "variety": "NORMAL",
            "tradingsymbol": trading_symbol,
            "symboltoken": self.get_symbol_token(trading_symbol),
            "transactiontype": "BUY",
            "exch_seg": "NFO",
            "ordertype": "MARKET",
            "producttype": "INTRADAY",
            "duration": "DAY",
            "quantity": LOT_SIZE,
        }

        try:
            order_id = self.client.placeOrder(order_params)
            print(f"Order placed: {signal['type']} {trading_symbol}, Order ID: {order_id}")
            self.active_trade = {
                'order_id': order_id,
                'type': signal['type'],
                'entry_price': ltp,
                'stop_loss': signal['sl'],
                'take_profit': signal['tp'],
                'symbol': trading_symbol
            }
            return True
        except Exception as e:
            print(f"Order placement failed: {e}")
            return False

    def monitor_trade(self, ltp):
        """Monitor LTP and exit if SL or TP is hit"""
        if not self.active_trade:
            return None

        trade_type = self.active_trade['type']
        current_price = ltp

        if trade_type == 'buy':
            if current_price <= self.active_trade['stop_loss']:
                profit = self.active_trade['stop_loss'] - self.active_trade['entry_price']
                self.exit_trade("STOPLOSS", profit)
                return {'type': 'exit', 'exit': self.active_trade['stop_loss'], 'profit': profit}
            elif current_price >= self.active_trade['take_profit']:
                profit = self.active_trade['take_profit'] - self.active_trade['entry_price']
                self.exit_trade("TAKEPROFIT", profit)
                return {'type': 'exit', 'exit': self.active_trade['take_profit'], 'profit': profit}
        elif trade_type == 'sell':
            if current_price >= self.active_trade['stop_loss']:
                profit = self.active_trade['entry_price'] - self.active_trade['stop_loss']
                self.exit_trade("STOPLOSS", profit)
                return {'type': 'exit', 'exit': self.active_trade['stop_loss'], 'profit': profit}
            elif current_price <= self.active_trade['take_profit']:
                profit = self.active_trade['entry_price'] - self.active_trade['take_profit']
                self.exit_trade("TAKEPROFIT", profit)
                return {'type': 'exit', 'exit': self.active_trade['take_profit'], 'profit': profit}
        return None

    def exit_trade(self, reason, profit):
        """Exit the active trade"""
        if self.active_trade:
            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": self.active_trade['symbol'],
                "symboltoken": self.get_symbol_token(self.active_trade['symbol']),
                "transactiontype": "SELL",
                "exch_seg": "NFO",
                "ordertype": "MARKET",
                "producttype": "INTRADAY",
                "duration": "DAY",
                "quantity": LOT_SIZE,
            }
            try:
                order_id = self.client.placeOrder(order_params)
                print(f"Trade exited: {reason}, Order ID: {order_id}, Profit: {profit:.2f} points")
            except Exception as e:
                print(f"Exit order failed: {e}")
            self.active_trade = None

# Example usage
if __name__ == "__main__":
    from data_fetcher import DataFetcher
    
    def dummy_callback(ltp, timestamp):
        print(f"LTP: {ltp}, Timestamp: {timestamp}")
    
    fetcher = DataFetcher(dummy_callback)
    executor = TradeExecutor(fetcher)
    
    # Test get_symbol_token
    sample_symbol = "NIFTY09APR2522050PE"  # Sample trading symbol
    try:
        token = executor.get_symbol_token(sample_symbol)
        print(f"Symbol: {sample_symbol}, Token: {token}")
    except Exception as e:
        print(f"Error: {e}")