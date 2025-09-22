#Import modules
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import vectorbt as vbt
import numpy as np

#create class
class MeanReversionStrategy:
    def __init__(self, symbol, period, interval, ema_length, atr_length, rsi_length, risk_per_trade=0.01, initial_capital=100):
        self.symbol = symbol
        self.period = period
        self.interval = interval
        self.ema_length = ema_length
        self.atr_length = atr_length
        self.rsi_length = rsi_length
        self.risk_per_trade = risk_per_trade
        self.initial_capital = initial_capital

        # Load, validate, calculate indicators, then filter data
        self.data = self.load_data()
        self.validate_data()
        self.calculate_indicators()
        self.filter_data()

    def load_data(self):
        #Downloading the data
        data = yf.download(self.symbol, period=self.period, interval=self.interval, progress=False)
        if data.empty:
            raise ValueError("Failed to download data. Check symbol/parameters.")
        
        # Convert index to UTC time
        if data.index.tz is None:
            data.index = pd.to_datetime(data.index).tz_localize('UTC')
        else:
            data.index = data.index.tz_convert('UTC')
        
        # Flatten multi-index columns
        #Flatten to fix Error:Strategy execution failed: Data must be 1-dimensional
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [f"{col[0]}_{col[1]}" for col in data.columns]
        
        return data

    def validate_data(self):
        # Expected column names (after flattening) 
        required_cols = [f"Open_{self.symbol}", f"High_{self.symbol}", f"Low_{self.symbol}", f"Close_{self.symbol}"]
        missing = [col for col in required_cols if col not in self.data.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")

    def calculate_indicators(self):
        #get data
        close_col = f"Close_{self.symbol}"
        high_col = f"High_{self.symbol}"
        low_col = f"Low_{self.symbol}"
        
        # Calculate indicators using the full dataset
        self.data["EMA"] = ta.ema(self.data[close_col], length=self.ema_length)
        self.data["RSI"] = ta.rsi(self.data[close_col], length=self.rsi_length)
        self.data["ATR"] = ta.atr(high=self.data[high_col], low=self.data[low_col], close=self.data[close_col], length=self.atr_length)
        
        # Drop rows with missing indicator values to get proper alignment
        self.data.dropna(subset=["EMA", "RSI", "ATR"], inplace=True)

    def filter_data(self):
        #filtering data to trading hours 08:00-11:30 
        # Convert data to the Toronto timezone for filtering
        toronto_data = self.data.tz_convert("America/Toronto")
        toronto_data = toronto_data.between_time("08:00", "11:30")
        if toronto_data.empty:
            raise ValueError("No data after time filtering")
        # Convert filtered data back to UTC 
        self.data = toronto_data.tz_convert("UTC")

    def calculate_position_size(self, entry_price, sl_price):
        #caculate position size based on stop loss distance
        sl_distance = np.abs(entry_price - sl_price) 
        risk_amount = 1  # Fixed risk per trade ($1)
        position_size = np.where(sl_distance > 0, risk_amount / sl_distance, 0)
        return pd.Series(position_size, index=entry_price.index)

    def generate_signals(self):
        #Generating trading signals, stop loss, and take profit
        close_col = f"Close_{self.symbol}"
        high_col = f"High_{self.symbol}"
        low_col = f"Low_{self.symbol}"
        
        atr = self.data['ATR']
        close = self.data[close_col]

        # Entry Conditions for long and short signals
        self.data['Long_Entry'] = (self.data[low_col] < (self.data['EMA'] - 1.5 * atr)) & (self.data['RSI'] < 50)
        self.data['Short_Entry'] = (self.data[high_col] > (self.data['EMA'] + 1.5 * atr)) & (self.data['RSI'] < 50)

        # Calculate SL and TP based on the Close price and ATR
        self.data['Long_SL'] = close - (atr * 1)
        self.data['Long_TP'] = close + (atr * 2)
        self.data['Short_SL'] = close + (atr * 1)
        self.data['Short_TP'] = close - (atr * 2)

        # Exit signals: Assume we exit when TP or SL is reached.
        self.data['Long_Exit'] = (close >= self.data['Long_TP']) | (close <= self.data['Long_SL'])
        self.data['Short_Exit'] = (close <= self.data['Short_TP']) | (close >= self.data['Short_SL'])
    def backtest(self):
        #run backtest with Vectorbt
        self.generate_signals()
        close_col = f"Close_{self.symbol}"
    
        long_entries = self.data['Long_Entry']
        short_entries = self.data['Short_Entry']
        long_exits = self.data['Long_Exit']
        short_exits = self.data['Short_Exit']
    
        # Calculate position size based on SL distance
        self.data['Long_Size'] = self.calculate_position_size(self.data[close_col], self.data['Long_SL'])
        self.data['Short_Size'] = self.calculate_position_size(self.data[close_col], self.data['Short_SL'])
    
        # Create portfolio 
        pf = vbt.Portfolio.from_signals(
            close=self.data[close_col],
            entries=long_entries,
            exits=long_exits,
            short_entries=short_entries,
            short_exits=short_exits,
            size=np.where(long_entries, self.data['Long_Size'], 
                          np.where(short_entries, self.data['Short_Size'], 0)),  # Apply size for long/short trades
            fees=0.0001,
            slippage=0.00005
        )
        return pf

    def run(self):
        return self.backtest()

if __name__ == "__main__":
    try:
        #run strategy
        strategy = MeanReversionStrategy(
            symbol="SPY",  
            period="60d",
            interval="15m",
            ema_length=50,
            atr_length=14,
            rsi_length=14,
            risk_per_trade=0.01,
            initial_capital=100
        )
        portfolio = strategy.run()
        print("Backtest Results:")
        print(portfolio.stats())

    except Exception as e:
        print(f"Error: {str(e)}")
