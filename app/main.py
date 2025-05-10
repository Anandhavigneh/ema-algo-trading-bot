# main.py
import asyncio
import platform
import ccxt.async_support as ccxt
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import json
import logging
from strategy import check_strategy, exitcondition
from trading import process_trade, place_market_buy_order, place_market_sell_order, get_balance, close_position, clear_mismatched_positions
from indicators import calculate_emas, fetch_binance_data
from telegram_ui import handle_message, handle_callback, start_bot, stop_bot, send_balance, send_status, send_trades, show_config, set_parameter, send_help, send_signal, load_config, save_config, get_main_menu
from time_utils import get_current_ist_time, get_current_utc_time, wait_for_next_candle, sync_time
from logger import setup_logging

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Setup logging
setup_logging()

# Configuration
TELEGRAM_TOKEN = "YOUR_TELEGRAM_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
LEVERAGE = [2]  # Using list to allow modification in callbacks

def load_binance_config():
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        binance_config = config.get('binance', {})
        if not binance_config.get('api_key') or not binance_config.get('api_secret'):
            raise ValueError("Missing api_key or api_secret in config.json")
        return binance_config
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        return {'api_key': '', 'api_secret': ''}

binance_config = load_binance_config()

exchange = ccxt.binance({
    'apiKey': binance_config['api_key'],
    'secret': binance_config['api_secret'],
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})
exchange.set_sandbox_mode(False)

application = Application.builder().token(TELEGRAM_TOKEN).build()
bot = application.bot

# Global variables
checked_symbols_state = {}
is_running = [False]
active_trade = [None]
exit_state = [None]
valid_symbols = set()
use_exitmin = [True]
trade_history = []
session_start_balance = [0.0]

config = load_config()
params = config.get("parameters", {})
ema_period1 = [params.get("ema1", 21)]
ema_period2 = [params.get("ema2", 60)]
ema_period3 = [params.get("ema3", 365)]
take_profit_pct = [params.get("tp", 0.5)]
stop_loss_pct = [params.get("sl", 2)]
exit_minutes = [params.get("exitmin", 2)]
use_exitmin = [params.get("use_exitmin", True)]
timeframe = [params.get("timeframe", "1m")]
margin_mode = "cross"

def init_from_config():
    config = load_config()
    params = config.get("parameters", {})
    ema_period1[0] = params.get("ema1", 21)
    ema_period2[0] = params.get("ema2", 60)
    ema_period3[0] = params.get("ema3", 365)
    take_profit_pct[0] = params.get("tp", 0.5)
    stop_loss_pct[0] = params.get("sl", 2)
    exit_minutes[0] = params.get("exitmin", 2)
    use_exitmin[0] = params.get("use_exitmin", True)
    timeframe[0] = params.get("timeframe", "1m")

def get_selected_coins():
    config = load_config()
    return config.get("selected_coins", [])

def has_active_trade():
    return active_trade[0] is not None

async def reset_global_states():
    checked_symbols_state.clear()
    active_trade[0] = None
    is_running[0] = False
    exit_state[0] = None
    logging.info("Global states have been reset.")

async def load_valid_symbols():
    global valid_symbols
    try:
        await sync_time(exchange)
        markets = await exchange.load_markets()
        valid_symbols = set(markets.keys())
        logging.info(f"Loaded {len(valid_symbols)} valid symbols from Binance")
        selected_coins = [coin for coin in get_selected_coins() if coin in valid_symbols]
        config = load_config()
        config['selected_coins'] = selected_coins
        save_config(config)
        logging.info(f"Updated config with valid coins: {selected_coins}")
    except Exception as e:
        logging.error(f"Error loading valid symbols: {e}")
        valid_symbols = set(get_selected_coins())

async def process_symbol(symbol):
    if symbol not in valid_symbols:
        logging.warning(f"Skipping {symbol}: not available on Binance")
        return
    try:
        if not has_active_trade():
            df = await fetch_binance_data(symbol, timeframe[0], exchange)
            if df.empty:
                return
            df = calculate_emas(df, ema_period1[0], ema_period2[0], ema_period3[0])
            order_info = await check_strategy(df, symbol, active_trade[0], checked_symbols_state, is_running[0])
            if order_info:
                entry_price = order_info['price']
                balance = await exchange.fetch_balance()
                usdt_free = balance['free'].get('USDT', 0.0)
                margin = usdt_free * 0.99
                notional_value = margin * LEVERAGE[0]
                position_size = notional_value / entry_price

                if notional_value < 10:
                    logging.warning(f"Notional value {notional_value:.2f} USDT for {symbol} below minimum 10 USDT")
                    position_size = 10 / entry_price
                    notional_value = 10
                    margin = notional_value / LEVERAGE[0]
                
                if margin > usdt_free:
                    logging.warning(f"Insufficient margin for {symbol}: Required {margin:.2f} USDT, Available {usdt_free:.2f} USDT")
                    await send_signal(f"⚠️ Insufficient margin for {symbol}: Required {margin:.2f} USDT, Available {usdt_free:.2f} USDT", bot, CHAT_ID)
                    return
                
                await exchange.set_margin_mode('cross', symbol)
                leverage_response = await exchange.set_leverage(LEVERAGE[0], symbol)
                logging.info(f"Set cross mode and leverage {LEVERAGE[0]}x for {symbol}: {leverage_response}")

                position_size_pct = (margin / usdt_free) * 100 if usdt_free > 0 else 0
                tp_price = entry_price * (1 + take_profit_pct[0] / 100)
                sl_price = entry_price * (1 - stop_loss_pct[0] / 100)
                message = f"""
🔺 LONG ENTRY ALERT 🔺  
📈 Symbol: {symbol}  
💰 Entry Price: {entry_price:.2f}  
📊 Order Details:  
   ├─ Amount: {position_size:.2f} {symbol.split('/')[0]}  
   ├─ Notional: {notional_value:.2f} USDT  
   ├─ Cost (Margin): {margin:.2f} USDT  
🎯 TP: {tp_price:.3f} | SL: {sl_price:.3f}  
📊 Position Size: {position_size_pct:.2f}% of Balance
                """
                await send_signal(message, bot, CHAT_ID)
                order = await place_market_buy_order(symbol, position_size, exchange)
                if order:
                    active_trade[0] = symbol
                    logging.info(f"Successfully placed long order for {symbol}: {position_size:.2f} at {entry_price:.2f}")
                    if 'fills' in order:
                        for fill in order['fills']:
                            logging.info(f"Fill: {fill['amount']:.2f} {symbol.split('/')[0]} at {fill['price']:.2f}")
                    await process_trade(symbol, entry_price, exchange, timeframe[0], ema_period1[0], ema_period2[0], ema_period3[0], take_profit_pct[0], stop_loss_pct[0], exit_minutes[0], use_exitmin[0], trade_history, active_trade, exit_state, fetch_binance_data, calculate_emas, exitcondition, place_market_sell_order, place_market_buy_order, get_balance, send_signal, get_current_ist_time, get_current_utc_time, LEVERAGE[0])
                else:
                    logging.error(f"Failed to place long order for {symbol}")
                    active_trade[0] = None
    except Exception as e:
        logging.error(f"Error processing {symbol}: {e}")

async def main_loop():
    try:
        await load_valid_symbols()
        selected_coins = [coin for coin in get_selected_coins() if coin in valid_symbols]
        logging.info(f"Processing symbols: {selected_coins}")
        while True:
            if is_running[0]:
                await wait_for_next_candle(timeframe[0])
                for symbol in selected_coins:
                    if has_active_trade():
                        logging.info(f"Active trade ({active_trade[0]}) in progress, skipping other symbols")
                        break
                    await process_symbol(symbol)
                await asyncio.sleep(1)
            else:
                logging.info("Bot is stopped. Waiting for restart...")
                await asyncio.sleep(5)
    except Exception as e:
        logging.error(f"Unexpected error in main loop: {e}")

async def start():
    try:
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        application.add_handler(CommandHandler("start", lambda update, context: start_bot(update, context, is_running, session_start_balance, init_from_config, sync_time, lambda: clear_mismatched_positions(exchange, get_selected_coins, LEVERAGE[0], lambda msg: send_signal(msg, bot, CHAT_ID)), lambda symbol: get_balance(symbol, exchange), get_selected_coins, timeframe, ema_period1, ema_period2, ema_period3, exit_minutes, LEVERAGE, lambda msg: send_signal(msg, bot, CHAT_ID), get_current_ist_time, get_current_utc_time)))
        application.add_handler(CommandHandler("menu", lambda update, context: update.message.reply_text("Main Menu:", reply_markup=get_main_menu())))
        application.add_handler(CommandHandler("stop", lambda update, context: stop_bot(update, context, is_running, active_trade, session_start_balance, trade_history, LEVERAGE, lambda symbol: get_balance(symbol, exchange), lambda: sync_time(exchange), lambda symbol, amount: place_market_sell_order(symbol, amount, exchange), reset_global_states, lambda msg: send_signal(msg, bot, CHAT_ID), get_current_ist_time, get_current_utc_time)))
        application.add_handler(CommandHandler("balance", lambda update, context: send_balance(update, context, exchange, timeframe, LEVERAGE, take_profit_pct, stop_loss_pct, active_trade, lambda: sync_time(exchange), get_current_ist_time, get_current_utc_time)))
        application.add_handler(CommandHandler("status", lambda update, context: send_status(update, context, is_running, timeframe, active_trade, get_current_ist_time, get_current_utc_time)))
        application.add_handler(CommandHandler("showconfig", lambda update, context: show_config(update, context, load_config)))
        application.add_handler(CommandHandler("set", lambda update, context: set_parameter(update, context, ema_period1, ema_period2, ema_period3, exit_minutes, use_exitmin, timeframe, take_profit_pct, stop_loss_pct, checked_symbols_state, load_config, save_config)))
        application.add_handler(CommandHandler("help", send_help))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: handle_message(update, context, CHAT_ID)))
        application.add_handler(CallbackQueryHandler(lambda update, context: handle_callback(update, context, LEVERAGE, use_exitmin, timeframe, load_config, save_config, lambda update, context: start_bot(update, context, is_running, session_start_balance, init_from_config, sync_time, lambda: clear_mismatched_positions(exchange, get_selected_coins, LEVERAGE[0], lambda msg: send_signal(msg, bot, CHAT_ID)), lambda symbol: get_balance(symbol, exchange), get_selected_coins, timeframe, ema_period1, ema_period2, ema_period3, exit_minutes, LEVERAGE, lambda msg: send_signal(msg, bot, CHAT_ID), get_current_ist_time, get_current_utc_time), lambda update, context: stop_bot(update, context, is_running, active_trade, session_start_balance, trade_history, LEVERAGE, lambda symbol: get_balance(symbol, exchange), lambda: sync_time(exchange), lambda symbol, amount: place_market_sell_order(symbol, amount, exchange), reset_global_states, lambda msg: send_signal(msg, bot, CHAT_ID), get_current_ist_time, get_current_utc_time), lambda update, context: send_balance(update, context, exchange, timeframe, LEVERAGE, take_profit_pct, stop_loss_pct, active_trade, lambda: sync_time(exchange), get_current_ist_time, get_current_utc_time), lambda update, context: send_status(update, context, is_running, timeframe, active_trade, get_current_ist_time, get_current_utc_time), lambda update, context: send_trades(update, context, trade_history, session_start_balance), send_help)))
        
        asyncio.create_task(main_loop())
        
        await asyncio.Event().wait()
    except Exception as e:
        logging.error(f"Unexpected error in bot loop: {e}")
    finally:
        await exchange.close()
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logging.info("Bot resources cleaned up.")

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(start())
    except Exception as e:
        logging.error(f"Error starting main loop: {e}")