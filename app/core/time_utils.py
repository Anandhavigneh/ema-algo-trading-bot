# time_utils.py
from datetime import datetime, timedelta, timezone
import asyncio
import logging

def get_current_utc_time():
    return datetime.now(timezone.utc).strftime("%H:%M")

def get_current_ist_time():
    ist_timezone = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist_timezone).strftime("%H:%M")

async def wait_for_next_candle(timeframe):
    now = datetime.now(timezone.utc)
    timeframe_minutes = {'1m': 1, '15m': 15, '30m': 30, '1h': 60}
    minutes = timeframe_minutes.get(timeframe, 1)
    # Align to the next candle boundary
    seconds_since_epoch = int(now.timestamp())
    seconds_to_next_candle = minutes * 60 - (seconds_since_epoch % (minutes * 60))
    next_candle_time = now + timedelta(seconds=seconds_to_next_candle)
    wait_time = seconds_to_next_candle + 1  # Add 1-second buffer to ensure candle close
    logging.info(f"Waiting {wait_time:.2f} seconds until the next {timeframe} candle close at {next_candle_time.strftime('%Y-%m-%d %H:%M:%S+00:00')}")
    await asyncio.sleep(wait_time)

async def sync_time(exchange):
    try:
        server_time = await exchange.fetch_time()
        local_time = int(datetime.now(timezone.utc).timestamp() * 1000)
        offset = server_time - local_time
        exchange.nonce = lambda: int(datetime.now(timezone.utc).timestamp() * 1000) + offset
        logging.info(f"Time synchronized with Binance server. Offset: {offset}ms")
    except Exception as e:
        logging.error(f"Error syncing time with Binance: {e}")