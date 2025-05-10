# indicators.py
import pandas as pd

def calculate_sma(prices, period):
    return prices.rolling(window=period, min_periods=1).mean()

def calculate_ema(prices, period):
    """
    Calculate a pure EMA without SMA smoothing.
    Initialize with the first price and compute EMA iteratively.
    """
    ema = prices.copy()
    alpha = 2 / (period + 1)
    ema.iloc[0] = prices.iloc[0]  # Initialize with first price
    for i in range(1, len(prices)):
        ema.iloc[i] = (prices.iloc[i] * alpha) + (ema.iloc[i - 1] * (1 - alpha))
    return ema

def calculate_emas(df, ema_period1, ema_period2, ema_period3):
    if df.empty:
        return df
    close = df['close']
    df['EMA1'] = calculate_ema(close, ema_period1)
    df['EMA2'] = calculate_ema(close, ema_period2)
    df['EMA3'] = calculate_ema(close, ema_period3)
    return df

async def fetch_binance_data(symbol, timeframe, exchange, limit=500, max_retries=5, retry_delay=5):
    for attempt in range(max_retries):
        try:
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not ohlcv:
                raise ValueError(f"No data returned for {symbol}")
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            return df
        except Exception as e:
            logging.error(f"Attempt {attempt + 1} failed for {symbol}: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                logging.error(f"All {max_retries} attempts failed for {symbol}. Skipping...")
                return pd.DataFrame()