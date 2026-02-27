import yfinance as yf
import pandas as pd

def test_stock(symbol):
    print(f"Testing {symbol}...")
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="1mo")
    if hist.empty:
        print(f"FAILED: {symbol} is empty")
    else:
        print(f"SUCCESS: {symbol} has {len(hist)} rows")
        print(hist.tail(1))

if __name__ == "__main__":
    test_stock("6187.TWO")
    test_stock("2330.TW")
    test_stock("AAPL")
