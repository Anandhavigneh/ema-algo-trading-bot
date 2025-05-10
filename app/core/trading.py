# trading.py
import ccxt.async_support as ccxt
import logging
import asyncio
from datetime import datetime, timezone

async def process_trade(symbol, entry_price, exchange, timeframe, ema_period1, ema_period2, ema_period3, take_profit_pct, stop_loss_pct, exit_minutes, use_exitmin, trade_history, active_trade, exit_state, fetch_binance_data, calculate_emas, exitcondition, place_market_sell_order, place_market_buy_order, get_balance, send_signal, get_current_ist_time, get_current_utc_time, LEVERAGE):
    trade_start_time = datetime.now(timezone.utc)

    while active_trade and active_trade == symbol:
        try:
            ticker = await exchange.fetch_ticker(symbol)
            current_price = ticker['last']

            positions = await exchange.fetch_positions([symbol])
            open_position = None
            normalized_symbol = symbol.replace('/', '')
            for pos in positions:
                pos_symbol_normalized = pos['symbol'].replace('/', '').replace(':USDT', '')
                if pos_symbol_normalized == normalized_symbol and float(pos['contracts']) > 0:
                    open_position = pos
                    break

            if open_position:
                actual_entry_price = float(open_position['entryPrice'])
                entry_amount = float(open_position['contracts'])
                side = open_position['side'].lower()
                take_profit_price = actual_entry_price * (1 + take_profit_pct / 100) if side == "long" else actual_entry_price * (1 - take_profit_pct / 100)
                stop_loss_price = actual_entry_price * (1 - stop_loss_pct / 100) if side == "long" else actual_entry_price * (1 + stop_loss_pct / 100)

                df = await fetch_binance_data(symbol, timeframe=timeframe)
                if df.empty:
                    return None
                df = calculate_emas(df, ema_period1, ema_period2, ema_period3)

                duration_minutes = (datetime.now(timezone.utc) - trade_start_time).total_seconds() / 60

                reason = None
                if side == "long" and current_price >= take_profit_price - 0.0001:
                    reason = "Take-profit"
                elif side == "long" and current_price <= stop_loss_price:
                    reason = "Stop-loss"
                elif side == "short" and current_price <= take_profit_price + 0.0001:
                    reason = "Take-profit"
                elif side == "short" and current_price >= stop_loss_price:
                    reason = "Stop-loss"
                elif await exitcondition(df, exit_state):
                    reason = "EMA Crossover Exit"
                elif use_exitmin and duration_minutes > exit_minutes:
                    reason = f"⏳ Time-Based ({exit_minutes} min)"

                if reason:
                    amount = float(open_position['contracts'])
                    if amount > 0.0001:
                        order = await (place_market_sell_order(symbol, amount, exchange) if side == "long" else place_market_buy_order(symbol, amount, exchange))
                        if order and order['status'] == 'closed':
                            logging.info(f"Closed {side} position for {symbol}: {amount} contracts")
                        else:
                            logging.error(f"Failed to close {side} position for {symbol}")
                            continue

                        usdt_balance = await get_balance('USDT', exchange)

                        if side == 'long':
                            profit_loss_pct = ((current_price - actual_entry_price) / actual_entry_price) * 100 * LEVERAGE
                            profit_loss_usdt = (current_price - actual_entry_price) * entry_amount * LEVERAGE
                        else:
                            profit_loss_pct = ((actual_entry_price - current_price) / actual_entry_price) * 100 * LEVERAGE
                            profit_loss_usdt = (actual_entry_price - current_price) * entry_amount * LEVERAGE

                        profit_loss_pct = round(profit_loss_pct, 2)
                        profit_loss_usdt = round(profit_loss_usdt, 2)

                        close_message = f"""
🚨 TRADE CLOSED 🚨  
📈 Symbol: {symbol} ({side.capitalize()})
📉 Exit Reason: {reason}  
💰 Exit Price: {current_price:.4f}  
📊 Performance:  
   ├─ Entry: {actual_entry_price:.4f}  
   ├─ P/L: {profit_loss_pct:.2f}% ({profit_loss_usdt:.2f} USDT)  
   └─ Balance: {usdt_balance:.2f} USDT  
⚙️ Leverage: {LEVERAGE}x  
📅 Date: {datetime.now().strftime("%Y-%m-%d")}  
🕒 Time: {get_current_ist_time()} IST | {get_current_utc_time()} UTC  
                        """

                        trade_history.append({
                            "symbol": symbol,
                            "entry_price": actual_entry_price,
                            "exit_price": current_price,
                            "pl_pct": profit_loss_pct,
                            "pl_usdt": profit_loss_usdt,
                            "reason": reason,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M IST")
                        })

                        if len(trade_history) > 10:
                            trade_history.pop(0)

                        await send_signal(close_message)
                        return order
            await asyncio.sleep(10)
        except Exception as e:
            logging.error(f"Error processing trade for {symbol}: {e}")
    return None

async def place_market_buy_order(symbol, amount, exchange):
    try:
        order = await exchange.create_market_buy_order(symbol, amount)
        logging.info(f"Market buy order placed: {order}")
        return order
    except Exception as e:
        logging.error(f"Error placing market buy order for {symbol}: {e}")
        return None

async def place_market_sell_order(symbol, amount, exchange):
    try:
        positions = await exchange.fetch_positions([symbol])
        position_exists = False
        
        for pos in positions:
            if pos['symbol'] == symbol and float(pos['contracts']) != 0:
                position_exists = True
                break
        
        if position_exists:
            for pos in positions:
                if pos['symbol'] == symbol and float(pos['contracts']) != 0:
                    await close_position(symbol, pos, exchange)
            await exchange.set_margin_mode('cross', symbol)
            leverage_response = await exchange.set_leverage(LEVERAGE, symbol)
            logging.info(f"Set cross mode and leverage {LEVERAGE}x for {symbol}: {leverage_response}")
        else:
            await exchange.set_margin_mode('cross', symbol)
            leverage_response = await exchange.set_leverage(LEVERAGE, symbol)
            logging.info(f"Margin mode set to cross and leverage set to {LEVERAGE}x for {symbol}: {leverage_response}")

        max_retries = 3
        retry_delay = 1  # seconds
        for attempt in range(max_retries):
            try:
                order = await exchange.create_market_sell_order(symbol, amount)
                logging.info(f"Market sell order placed: {order}")
                return order
            except ccxt.BaseError as e:
                if str(e).find('-4131') != -1 and attempt < max_retries - 1:
                    logging.warning(f"PERCENT_PRICE filter error for {symbol} (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    raise e
        # Fallback to limit sell order after retries fail
        try:
            order_book = await exchange.fetch_order_book(symbol)
            best_bid = order_book['bids'][0][0] if order_book['bids'] else None
            if best_bid:
                limit_price = best_bid * 0.999
                order = await exchange.create_limit_sell_order(symbol, amount, limit_price)
                logging.info(f"Limit sell order placed for {symbol} at {limit_price}: {order}")
                return order
            else:
                logging.error(f"No bid price available in order book for {symbol}")
                return None
        except Exception as fallback_e:
            logging.error(f"Error placing limit sell order for {symbol}: {fallback_e}")
            return None
    except Exception as e:
        logging.error(f"Error placing market sell order for {symbol}: {e}")
        return None

async def get_balance(symbol, exchange, retries=5, delay=5):
    for attempt in range(retries):
        try:
            balance = await exchange.fetch_balance()
            return balance['total'].get(symbol, 0.0)
        except ccxt.AuthenticationError as e:
            logging.error(f"Authentication error fetching balance: {e}")
            raise
        except Exception as e:
            logging.error(f"Error fetching balance for {symbol} (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(delay)
            else:
                return 0.0

async def close_position(symbol, position, exchange, send_signal):
    try:
        amount = abs(float(position['contracts']))
        side = 'buy' if position['side'] == 'short' else 'sell'
        order = await exchange.create_market_order(symbol, side, amount)
        logging.info(f"Closed {position['side']} position for {symbol}: {amount} contracts")
        await send_signal(f"🔔 Closed existing {position['side']} position for {symbol}: {amount} contracts")
        return order
    except Exception as e:
        logging.error(f"Error closing position for {symbol}: {e}")
        return None

async def clear_mismatched_positions(exchange, get_selected_coins, LEVERAGE, send_signal):
    try:
        selected_coins = get_selected_coins()
        positions = await exchange.fetch_positions(selected_coins)
        for position in positions:
            symbol = position['symbol']
            if float(position['contracts']) != 0:
                await close_position(symbol, position, exchange, send_signal)
                await exchange.set_margin_mode('cross', symbol)
                leverage_response = await exchange.set_leverage(LEVERAGE, symbol)
                logging.info(f"Set cross mode and leverage {LEVERAGE}x for {symbol}: {leverage_response}")
    except Exception as e:
        logging.error(f"Error clearing mismatched positions: {e}")