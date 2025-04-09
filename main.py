# main.py
from data_fetcher import DataFetcher
from data_storage import DataStorage
from trading_logic import TradingLogic
from trade_executor import TradeExecutor
from config import TRADING_HOURS_START, TRADING_HOURS_END
import time
from datetime import datetime

def main():
    storage = DataStorage()
    logic = TradingLogic()
    fetcher = DataFetcher(lambda ltp, timestamp: storage.update(ltp, timestamp))
    executor = TradeExecutor(fetcher)

    fetcher.start()
    print("Nifty Trading System started.")

    try:
        while True:
            current_time = datetime.now().strftime("%H:%M")
            print(f"Current time: {current_time}")
            if not (TRADING_HOURS_START <= current_time <= TRADING_HOURS_END):
                print("Outside trading hours. Waiting...")
                time.sleep(60)
                continue

            candles = storage.get_candles()
            current_candle = storage.get_current_candle()
            print(f"Candles: {len(candles)}, Current: {current_candle}")

            if current_candle and len(candles) > 0:
                # No new trades after 15:15
                if current_time < "15:15":
                    signal = logic.evaluate(candles, current_candle)
                    if signal:
                        executor.place_order(signal, current_candle['Close'])
                        print(f"Trade initiated: {signal}")
                
                # Exit open trades at 15:15
                if current_time >= "15:15" and executor.active_trade:
                    ltp = current_candle['Close']
                    trade_type = executor.active_trade['type']
                    if trade_type == 'buy':
                        profit = ltp - executor.active_trade['entry_price']
                    else:  # 'sell'
                        profit = executor.active_trade['entry_price'] - ltp
                    executor.log_exit("END_OF_DAY", profit)
                    print(f"Forced exit at 15:15: Profit: {profit:.2f} points")
                    executor.active_trade = None  # Clear trade after forced exit
                
                # Regular monitoring before 15:15
                elif executor.active_trade:
                    ltp = current_candle['Close']
                    exit_signal = executor.monitor_trade(ltp)
                    if exit_signal:
                        print(f"Trade exited: {exit_signal}")

            time.sleep(1)

    except KeyboardInterrupt:
        print("Shutting down...")
        fetcher.stop()
    except Exception as e:
        print(f"Error: {e}")
        fetcher.stop()

if __name__ == "__main__":
    main()