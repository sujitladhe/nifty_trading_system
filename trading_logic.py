# trading_logic.py
# Implements the trend-following pullback strategy for Nifty options

from config import MA_PERIOD, RISK_REWARD_RATIO, BUFFER_CANDLES
import pandas as pd  # Added import here

class TradingLogic:
    def __init__(self):
        self.position = None  # None, 'long', or 'short'
        self.entry_price = None
        self.stop_loss = None
        self.take_profit = None
        self.consolidation_window = 5  # Max candles for consolidation
        self.ma_buffer = 10  # Points buffer for "near MA"

    def evaluate(self, candles, current_candle):
        """Evaluate trading signals based on candles and current price"""
        if self.position is not None:
            return None  # No new trades if already in a position

        if len(candles) < MA_PERIOD:
            return None  # Not enough data for 20 MA

        # Determine MA direction (last two values)
        ma_direction = 1 if candles['MA_20'].iloc[-1] > candles['MA_20'].iloc[-2] else -1

        # Look back up to consolidation_window + 1 candles
        lookback = min(len(candles), self.consolidation_window + 1)
        recent_candles = candles.tail(lookback)

        if ma_direction == 1:  # Uptrend - Look for buy (CE)
            for i in range(len(recent_candles) - 1):
                candle = recent_candles.iloc[i]
                if candle['Close'] < candle['Open']:  # Red candle
                    # Check if near or crossed MA
                    close_to_ma = (abs(candle['Close'] - candle['MA_20']) <= self.ma_buffer or
                                  candle['Low'] <= candle['MA_20'] <= candle['High'])
                    if close_to_ma or i < len(recent_candles) - 1:
                        # Check breakout with current candle
                        if current_candle['High'] > candle['High']:
                            self.entry_price = candle['High'] + 0.05  # Small buffer
                            self.stop_loss = candle['Low']
                            self.take_profit = self.entry_price + RISK_REWARD_RATIO * (self.entry_price - self.stop_loss)
                            self.position = 'long'
                            return {'type': 'buy', 'entry': self.entry_price, 'sl': self.stop_loss, 'tp': self.take_profit}
        
        elif ma_direction == -1:  # Downtrend - Look for sell (PE)
            for i in range(len(recent_candles) - 1):
                candle = recent_candles.iloc[i]
                if candle['Close'] > candle['Open']:  # Green candle
                    # Check if near or crossed MA
                    close_to_ma = (abs(candle['Close'] - candle['MA_20']) <= self.ma_buffer or
                                  candle['Low'] <= candle['MA_20'] <= candle['High'])
                    if close_to_ma or i < len(recent_candles) - 1:
                        # Check breakout with current candle
                        if current_candle['Low'] < candle['Low']:
                            self.entry_price = candle['Low'] - 0.05  # Small buffer
                            self.stop_loss = candle['High']
                            self.take_profit = self.entry_price - RISK_REWARD_RATIO * (self.stop_loss - self.entry_price)
                            self.position = 'short'
                            return {'type': 'sell', 'entry': self.entry_price, 'sl': self.stop_loss, 'tp': self.take_profit}

        return None

    def check_exit(self, current_price):
        """Check if stop-loss or take-profit is hit"""
        if self.position == 'long':
            if current_price <= self.stop_loss:
                profit = self.stop_loss - self.entry_price
                self.reset()
                return {'type': 'exit', 'exit': self.stop_loss, 'profit': profit}
            elif current_price >= self.take_profit:
                profit = self.take_profit - self.entry_price
                self.reset()
                return {'type': 'exit', 'exit': self.take_profit, 'profit': profit}
        elif self.position == 'short':
            if current_price >= self.stop_loss:
                profit = self.entry_price - self.stop_loss
                self.reset()
                return {'type': 'exit', 'exit': self.stop_loss, 'profit': profit}
            elif current_price <= self.take_profit:
                profit = self.entry_price - self.take_profit
                self.reset()
                return {'type': 'exit', 'exit': self.take_profit, 'profit': profit}
        return None

    def reset(self):
        """Reset position after trade exits"""
        self.position = None
        self.entry_price = None
        self.stop_loss = None
        self.take_profit = None

# Example usage
if __name__ == "__main__":
    logic = TradingLogic()
    # Simulate candles (replace with real data from data_storage)
    candles = pd.DataFrame({
        'Timestamp': pd.date_range(start='2025-04-07 09:15', periods=25, freq='1min'),
        'Open': [50000 + i for i in range(25)],
        'High': [50005 + i for i in range(25)],
        'Low': [49995 + i for i in range(25)],
        'Close': [50002 + i for i in range(25)]
    })
    candles['MA_20'] = candles['Close'].rolling(window=MA_PERIOD).mean()
    current_candle = {'High': 50030, 'Low': 50020, 'Close': 50025}
    
    signal = logic.evaluate(candles, current_candle)
    print("Signal:", signal)
    if signal:
        exit_signal = logic.check_exit(50035)
        print("Exit:", exit_signal)