# telegram_ui.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import json
import logging

def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Start Bot", callback_data='start_bot'), InlineKeyboardButton("🛑 Stop Bot", callback_data='stop_bot')],
        [InlineKeyboardButton("💰 Balance", callback_data='balance'), InlineKeyboardButton("📡 Status", callback_data='status')],
        [InlineKeyboardButton("⚙️ Config", callback_data='config'), InlineKeyboardButton("📊 Trades", callback_data='trades')],
        [InlineKeyboardButton("🔧 Settings", callback_data='settings'), InlineKeyboardButton("🆘 Help", callback_data='help')],
    ])

def get_config_menu(LEVERAGE):
    config = load_config()
    params = config.get("parameters", {})
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"EMA1: {params.get('ema1', 21)}", callback_data='set_ema1'), 
         InlineKeyboardButton(f"EMA2: {params.get('ema2', 60)}", callback_data='set_ema2')],
        [InlineKeyboardButton(f"EMA3: {params.get('ema3', 365)}", callback_data='set_ema3')],
        [InlineKeyboardButton(f"Max Duration: {params.get('exitmin', 2)}m", callback_data='set_max_duration'),
         InlineKeyboardButton(f"Leverage: {LEVERAGE}x", callback_data='set_leverage')],
        [InlineKeyboardButton("🔄 Refresh", callback_data='config'), 
         InlineKeyboardButton("⬅️ Back", callback_data='menu')],
    ])

def get_settings_menu():
    config = load_config()
    params = config.get("parameters", {})
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⏳ ExitMin: {'On' if params.get('use_exitmin', True) else 'Off'}", callback_data='set_use_exitmin')],
        [InlineKeyboardButton(f"⏰ Timeframe: {params.get('timeframe', '1m')}", callback_data='set_timeframe')],
        [InlineKeyboardButton("⬅️ Back to Config", callback_data='menu')],
    ])

def get_exitmin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("on", callback_data='set_exitmin_on'),
         InlineKeyboardButton("off", callback_data='set_exitmin_off')],
        [InlineKeyboardButton("⬅️ Back to Config", callback_data='menu')],
    ])

def get_timeframe_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1m", callback_data='set_timeframe_1m'),
         InlineKeyboardButton("15m", callback_data='set_timeframe_15m')],
        [InlineKeyboardButton("30m", callback_data='set_timeframe_30m'),
         InlineKeyboardButton("1h", callback_data='set_timeframe_1h')],
        [InlineKeyboardButton("⬅️ Back to Settings", callback_data='settings')],
    ])

def get_leverage_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1x", callback_data='set_leverage_1'),
         InlineKeyboardButton("2x", callback_data='set_leverage_2'),
         InlineKeyboardButton("3x", callback_data='set_leverage_3'),
         InlineKeyboardButton("4x", callback_data='set_leverage_4'),
         InlineKeyboardButton("5x", callback_data='set_leverage_5')],
        [InlineKeyboardButton("6x", callback_data='set_leverage_6'),
         InlineKeyboardButton("7x", callback_data='set_leverage_7'),
         InlineKeyboardButton("8x", callback_data='set_leverage_8'),
         InlineKeyboardButton("9x", callback_data='set_leverage_9'),
         InlineKeyboardButton("10x", callback_data='set_leverage_10')],
        [InlineKeyboardButton("⬅️ Back to Config", callback_data='config')],
    ])

async def handle_message(update: Update, context: CallbackContext, CHAT_ID):
    if update.message and update.message.chat and str(update.message.chat.id) == CHAT_ID:
        if update.message.text == "/menu":
            await update.message.reply_text("Main Menu:", reply_markup=get_main_menu())
        elif update.message.text not in ["/start", "/stop", "/balance", "/status", "/showconfig", "/set", "/help"]:
            await update.message.reply_text("Unknown command! Use the menu below:", reply_markup=get_main_menu())
    else:
        logging.warning(f"Unauthorized access attempt from chat ID: {update.message.chat.id}")

async def handle_callback(update: Update, context: CallbackContext, LEVERAGE, use_exitmin, timeframe, load_config, save_config, start_bot, stop_bot, send_balance, send_status, send_trades, send_help):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'start_bot':
        await start_bot(update, context)
    elif data == 'stop_bot':
        await stop_bot(update, context)
    elif data == 'balance':
        await send_balance(update, context)
    elif data == 'status':
        await send_status(update, context)
    elif data == 'config':
        new_text = "Configuration Menu:"
        new_markup = get_config_menu(LEVERAGE)
        if query.message.text != new_text or str(query.message.reply_markup) != str(new_markup):
            await query.edit_message_text(new_text, reply_markup=new_markup)
    elif data == 'settings':
        new_text = "Settings Menu:"
        new_markup = get_settings_menu()
        if query.message.text != new_text or str(query.message.reply_markup) != str(new_markup):
            await query.edit_message_text(new_text, reply_markup=new_markup)
    elif data == 'trades':
        await send_trades(update, context)
    elif data == 'help':
        await send_help(update, context)
    elif data.startswith('set_'):
        param = data.replace('set_', '')
        config = load_config()
        params = config.get("parameters", {})
        if param == 'use_exitmin':
            await query.edit_message_text("Select ExitMin:", reply_markup=get_exitmin_menu())
        elif param == 'exitmin_on':
            params['use_exitmin'] = True
            config['parameters'] = params
            save_config(config)
            use_exitmin[0] = True
            await query.edit_message_text("Exit Minutes condition enabled", reply_markup=get_main_menu())
        elif param == 'exitmin_off':
            params['use_exitmin'] = False
            config['parameters'] = params
            save_config(config)
            use_exitmin[0] = False
            await query.edit_message_text("Exit Minutes condition disabled", reply_markup=get_main_menu())
        elif param == 'timeframe':
            await query.edit_message_text("Select Timeframe:", reply_markup=get_timeframe_menu())
        elif param == 'timeframe_1m':
            params['timeframe'] = '1m'
            config['parameters'] = params
            save_config(config)
            timeframe[0] = '1m'
            await query.edit_message_text("Timeframe set to 1m", reply_markup=get_settings_menu())
        elif param == 'timeframe_15m':
            params['timeframe'] = '15m'
            config['parameters'] = params
            save_config(config)
            timeframe[0] = '15m'
            await query.edit_message_text("Timeframe set to 15m", reply_markup=get_settings_menu())
        elif param == 'timeframe_30m':
            params['timeframe'] = '30m'
            config['parameters'] = params
            save_config(config)
            timeframe[0] = '30m'
            await query.edit_message_text("Timeframe set to 30m", reply_markup=get_settings_menu())
        elif param == 'timeframe_1h':
            params['timeframe'] = '1h'
            config['parameters'] = params
            save_config(config)
            timeframe[0] = '1h'
            await query.edit_message_text("Timeframe set to 1h", reply_markup=get_settings_menu())
        elif param == 'leverage':
            await query.edit_message_text("Select Leverage:", reply_markup=get_leverage_menu())
        elif param.startswith('leverage_'):
            leverage_value = int(param.split('_')[1])
            LEVERAGE[0] = leverage_value
            await query.edit_message_text(f"Leverage set to {leverage_value}x", reply_markup=get_config_menu(LEVERAGE[0]))
        else:
            instruction = f"Use /set {param} <value> to change this parameter."
            await query.edit_message_text(instruction, reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data='config')],
                [InlineKeyboardButton("⬅️ Back", callback_data='menu')]
            ]))
    elif data == 'menu':
        new_text = "Main Menu:"
        new_markup = get_main_menu()
        if query.message.text != new_text or str(query.message.reply_markup) != str(new_markup):
            await query.edit_message_text(new_text, reply_markup=new_markup)

async def start_bot(update: Update, context: CallbackContext, is_running, session_start_balance, init_from_config, sync_time, clear_mismatched_positions, get_balance, get_selected_coins, timeframe, ema_period1, ema_period2, ema_period3, exit_minutes, LEVERAGE, send_signal, get_current_ist_time, get_current_utc_time):
    if not is_running[0]:
        is_running[0] = True
        init_from_config()
        await sync_time()
        await clear_mismatched_positions()
        usdt_balance = await get_balance('USDT')
        session_start_balance[0] = usdt_balance
        start_message = f"""
✅ TRADING BOT ACTIVATED ✅

💰 Account Overview:
   ├─ Starting Balance: {usdt_balance:.2f} USDT
   ├─ Margin Available: 100%
   └─ Risk Level: Low

⚙️ Settings:
   ├─ Leverage: {LEVERAGE[0]}x
   ├─ Coins: {', '.join(get_selected_coins())}
   ├─ Strategy: EMA Crossover ({timeframe[0]})
   └─ Margin Mode: cross

📊 Parameters:
   ├─ EMA1: {ema_period1[0]}
   ├─ EMA2: {ema_period2[0]}
   └─ EMA3: {ema_period3[0]}
   └─ Max Duration: {exit_minutes[0]}m

📅 Date: {datetime.now().strftime("%Y-%m-%d")}
🕒 Time: {get_current_ist_time()} IST | {get_current_utc_time()} UTC
        """
        if update.callback_query:
            query = update.callback_query
            await query.edit_message_text(start_message, reply_markup=get_main_menu())
        else:
            await update.message.reply_text(start_message, reply_markup=get_main_menu())
        await send_signal(start_message)
        logging.info("Bot started fresh.")
    else:
        if update.callback_query:
            await update.callback_query.edit_message_text("Bot is already running!", reply_markup=get_main_menu())
        else:
            await update.message.reply_text("Bot is already running!", reply_markup=get_main_menu())

async def stop_bot(update: Update, context: CallbackContext, is_running, active_trade, session_start_balance, trade_history, LEVERAGE, get_balance, sync_time, place_market_sell_order, reset_global_states, send_signal, get_current_ist_time, get_current_utc_time):
    if is_running[0]:
        start_balance = session_start_balance[0]
        if active_trade[0]:
            await sync_time()
            try:
                positions = await exchange.fetch_positions([active_trade[0]])
                normalized_symbol = active_trade[0].replace('/', '')
                for pos in positions:
                    pos_symbol_normalized = pos['symbol'].replace('/', '').replace(':USDT', '')
                    if pos_symbol_normalized == normalized_symbol and pos['side'] == 'long' and float(pos['contracts']) > 0:
                        amount = float(pos['contracts'])
                        logging.info(f"Closing long position for {active_trade[0]}: {amount} contracts")
                        order = await place_market_sell_order(active_trade[0], amount)
                        if order and order['status'] == 'closed':
                            logging.info(f"Successfully closed long position for {active_trade[0]}: {amount} contracts")
                            await send_signal(f"🔔 Closed long position for {active_trade[0]}: {amount} contracts on bot stop")
                        else:
                            logging.error(f"Failed to close long position for {active_trade[0]}")
            except Exception as e:
                logging.error(f"Error closing position for {active_trade[0]}: {e}")
            active_trade[0] = None
        usdt_balance = await get_balance('USDT')
        net_pl_usdt = usdt_balance - start_balance
        net_pl_pct = (net_pl_usdt / start_balance) * 100 if start_balance > 0 else -100.00
        stop_message = f"""
🚫 BOT DEACTIVATED 🚫  
📊 Session Report:  
   ├─ Start Balance: {start_balance:.2f} USDT  
   ├─ End Balance: {usdt_balance:.2f} USDT  
   ├─ Net P/L: {net_pl_pct:.2f}% ({net_pl_usdt:.2f} USDT)  
   └─ Trades: {len(trade_history)}  
⚙️ Leverage: {LEVERAGE[0]}x  
📅 Date: {datetime.now().strftime("%Y-%m-%d")}  
🕒 Time: {get_current_ist_time()} IST | {get_current_utc_time()} UTC  
📋 Summary: Session ended
        """
        await reset_global_states()
        if update.callback_query:
            query = update.callback_query
            await query.edit_message_text(stop_message, reply_markup=get_main_menu())
        else:
            await update.message.reply_text(stop_message, reply_markup=get_main_menu())
        await send_signal(stop_message)
        logging.info("Bot stopped.")
    else:
        if update.callback_query:
            await update.callback_query.edit_message_text("Bot is already stopped!", reply_markup=get_main_menu())
        else:
            await update.message.reply_text("Bot is already stopped!", reply_markup=get_main_menu())

async def send_balance(update: Update, context: CallbackContext, exchange, timeframe, LEVERAGE, take_profit_pct, stop_loss_pct, active_trade, sync_time, get_current_ist_time, get_current_utc_time):
    try:
        await sync_time()
        balance = await exchange.fetch_balance()
        usdt_balance = balance['total'].get('USDT', 0.0) if balance.get('total') else 0.0
        margin_used = balance['used'].get('USDT', 0.0) if balance.get('used') else 0.0
        equity = usdt_balance + margin_used if margin_used else usdt_balance
        margin_pct = (margin_used / equity * 100) if equity > 0 else 0
        
        message = f"""
💰 ACCOUNT STATUS 💰

📈 Current Balance:
   ├─ USDT: {usdt_balance:.2f}
   ├─ Margin Used: {margin_used:.2f} USDT ({margin_pct:.1f}%)
   └─ Equity: {equity:.2f} USDT

⚙️ Settings:
   ├─ Timeframe: {timeframe[0]}
   ├─ Margin Mode: cross
   ├─ Leverage: {LEVERAGE[0]}x
   ├─ Take-Profit: {take_profit_pct[0]}%
   └─ Stop-Loss: {stop_loss_pct[0]}%

📊 Open Positions:
   └─ {active_trade[0] if active_trade[0] else 'None'}

📅 Date: {datetime.now().strftime("%Y-%m-%d")}
🕒 Time: {get_current_ist_time()} IST | {get_current_utc_time()} UTC
"""
        if update.callback_query:
            query = update.callback_query
            back_markup = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menu", callback_data='menu')]])
            if query.message.text != message or str(query.message.reply_markup) != str(back_markup):
                await query.edit_message_text(message, reply_markup=back_markup)
        else:
            await update.message.reply_text(message, reply_markup=get_main_menu())
    except ccxt.AuthenticationError as e:
        logging.error(f"Authentication error fetching balance: {e}")
        message = "Authentication error: Please check your API credentials in config.json"
        if update.callback_query:
            query = update.callback_query
            back_markup = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menu", callback_data='menu')]])
            if query.message.text != message or str(query.message.reply_markup) != str(back_markup):
                await query.edit_message_text(message, reply_markup=back_markup)
        else:
            await update.message.reply_text(message, reply_markup=get_main_menu())
    except Exception as e:
        logging.error(f"Error fetching balance: {e}")
        message = "Sorry, I couldn't fetch your balance at the moment. Please check your API credentials."
        if update.callback_query:
            query = update.callback_query
            back_markup = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menu", callback_data='menu')]])
            if query.message.text != message or str(query.message.reply_markup) != str(back_markup):
                await query.edit_message_text(message, reply_markup=back_markup)
        else:
            await update.message.reply_text(message, reply_markup=get_main_menu())

async def send_status(update: Update, context: CallbackContext, is_running, timeframe, active_trade, get_current_ist_time, get_current_utc_time):
    status_message = f"""
📡 BOT STATUS UPDATE 📡

{'✅ Running' if is_running[0] else '❌ Stopped'}
⏰ Timeframe: {timeframe[0]}
⚖️ Margin Mode: cross
📊 Active Trade: {active_trade[0] if active_trade[0] else 'None'}
📅 Date: {datetime.now().strftime("%Y-%m-%d")}
🕒 Time: {get_current_ist_time()} IST | {get_current_utc_time()} UTC
"""
    if update.callback_query:
        query = update.callback_query
        back_markup = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menu", callback_data='menu')]])
        if query.message.text != status_message or str(query.message.reply_markup) != str(back_markup):
            await query.edit_message_text(status_message, reply_markup=back_markup)
    else:
        await update.message.reply_text(status_message, reply_markup=get_main_menu())

async def send_trades(update: Update, context: CallbackContext, trade_history, session_start_balance):
    total_trades = len(trade_history)
    winning_trades = sum(1 for trade in trade_history if trade['pl_pct'] > 0)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    avg_win = sum(trade['pl_pct'] for trade in trade_history if trade['pl_pct'] > 0) / winning_trades if winning_trades > 0 else 0
    avg_loss = sum(trade['pl_pct'] for trade in trade_history if trade['pl_pct'] < 0) / (total_trades - winning_trades) if total_trades - winning_trades > 0 else 0
    max_drawdown = min([0] + [trade['pl_pct'] for trade in trade_history]) if trade_history else 0
    start_balance = session_start_balance[0]

    message = f"""
📊 Trade Statistics:

Total Trades: {total_trades}
Winning Trades: {winning_trades}
Win Rate: {win_rate:.1f}%
Avg Win: {avg_win:.2f}%
Avg Loss: {avg_loss:.2f}%
Max Drawdown: {max_drawdown:.2f}%

Current Session:
Start Balance: {start_balance:.2f} USDT
"""
    if update.callback_query:
        query = update.callback_query
        back_markup = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menu", callback_data='menu')]])
        if query.message.text != message or str(query.message.reply_markup) != str(back_markup):
            await query.edit_message_text(message, reply_markup=back_markup)
    else:
        await update.message.reply_text(message, reply_markup=get_main_menu())

async def show_config(update: Update, context: CallbackContext, load_config):
    config = load_config()
    param_config = config.get('parameters', {})
    config_message = json.dumps(param_config, indent=4)
    await update.message.reply_text(f"Current param config:\n\n{config_message}", reply_markup=get_main_menu())

async def set_parameter(update: Update, context: CallbackContext, ema_period1, ema_period2, ema_period3, exit_minutes, use_exitmin, timeframe, take_profit_pct, stop_loss_pct, checked_symbols_state, load_config, save_config):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /set <parameter> <value>\nValid parameters: ema1, ema2, ema3, exitmin, use_exitmin, timeframe, tp, sl")
        return
    
    param, value = context.args[0].lower(), context.args[1].lower()
    valid_params = ['ema1', 'ema2', 'ema3', 'exitmin', 'use_exitmin', 'timeframe', 'tp', 'sl']
    
    if param not in valid_params:
        await update.message.reply_text(f"Parameter {param} not found. Use: {', '.join(valid_params)}")
        return
    
    config = load_config()
    params = config.get("parameters", {})
    
    try:
        if param == 'ema1':
            ema_period1[0] = int(value)
            params['ema1'] = ema_period1[0]
            await update.message.reply_text(f"EMA1 set to {ema_period1[0]}")
        elif param == 'ema2':
            ema_period2[0] = int(value)
            params['ema2'] = ema_period2[0]
            await update.message.reply_text(f"EMA2 set to {ema_period2[0]}")
        elif param == 'ema3':
            ema_period3[0] = int(value)
            params['ema3'] = ema_period3[0]
            await update.message.reply_text(f"EMA3 set to {ema_period3[0]}")
        elif param == 'exitmin':
            exit_minutes[0] = float(value)
            params['exitmin'] = exit_minutes[0]
            await update.message.reply_text(f"Exit Minutes set to {exit_minutes[0]}")
        elif param == 'use_exitmin':
            if value in ['on', 'true', '1']:
                use_exitmin[0] = True
                params['use_exitmin'] = True
                await update.message.reply_text("Exit Minutes condition enabled", reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ Config", callback_data='config')]
                ]))
            elif value in ['off', 'false', '0']:
                use_exitmin[0] = False
                params['use_exitmin'] = False
                await update.message.reply_text("Exit Minutes condition disabled", reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ Config", callback_data='config')]
                ]))
            else:
                await update.message.reply_text("Use 'on' or 'off' for use_exitmin")
                return
        elif param == 'timeframe':
            valid_timeframes = ['1m', '15m', '30m', '1h']
            if value in valid_timeframes:
                if timeframe[0] != value:  # Only reset if timeframe changes
                    timeframe[0] = value
                    params['timeframe'] = timeframe[0]
                    checked_symbols_state.clear()  # Reset state to avoid stale signals
                    logging.info(f"Timeframe changed to {timeframe[0]}. Cleared checked_symbols_state.")
                    await update.message.reply_text(f"Timeframe set to {timeframe[0]}", reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⚙️ Config", callback_data='config')]
                    ]))
                else:
                    await update.message.reply_text(f"Timeframe already set to {timeframe[0]}", reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⚙️ Config", callback_data='config')]
                    ]))
            else:
                await update.message.reply_text(f"Invalid timeframe. Use: {', '.join(valid_timeframes)}")
                return
        elif param == 'tp':
            take_profit_pct[0] = float(value)
            params['tp'] = take_profit_pct[0]
            await update.message.reply_text(f"Take-Profit set to {take_profit_pct[0]}%")
        elif param == 'sl':
            stop_loss_pct[0] = float(value)
            params['sl'] = stop_loss_pct[0]
            await update.message.reply_text(f"Stop-Loss set to {stop_loss_pct[0]}%")
        
        config['parameters'] = params
        save_config(config)
        logging.info(f"Parameter {param} set to {value} and saved to config")
    except ValueError:
        await update.message.reply_text("Invalid value. Use appropriate format for each parameter.")

async def send_help(update: Update, context: CallbackContext):
    help_message = """
Basic Commands:
    /set <parameter> <value> - Changes configuration values

Strategy:
    📈 EMA Crossover (Long-Only): Configurable EMA1, EMA2, EMA3

Configuration Parameters:
    📊 ema1 - Short EMA period (e.g., 20)
    📊 ema2 - Medium EMA period (e.g., 50)
    📊 ema3 - Long EMA period (e.g., 200)
    🎯 tp - Take-profit %: (0.5)
    🛑 sl - Stop-loss %: (2)
    ⏳ exitmin - Max trade duration in minutes (default: 2)
    ✅ use_exitmin - Enable/disable time-based exit (on/off, default: on)
    ⏰ timeframe - Chart timeframe (1m, 15m, 30m, 1h, default: 1m)
    🔧 leverage - Leverage value (e.g., 2, 10)
"""
    back_markup = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data='menu')]])
    
    if update.callback_query:
        query = update.callback_query
        if query.message.text != help_message or str(query.message.reply_markup) != str(back_markup):
            await query.edit_message_text(help_message, reply_markup=back_markup)
    else:
        await update.message.reply_text(help_message, reply_markup=back_markup)

async def send_signal(message, bot, CHAT_ID, retries=3, delay=5):
    for attempt in range(retries):
        try:
            await bot.send_message(chat_id=CHAT_ID, text=message)
            logging.info(f"Signal sent: {message}")
            return
        except TimedOut as e:
            logging.error(f"Telegram timeout on attempt {attempt + 1}/{retries}: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(delay)
        except Exception as e:
            logging.error(f"Error sending signal on attempt {attempt + 1}/{retries}: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(delay)
    logging.error(f"Failed to send signal after {retries} attempts: {message}")

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

def save_config(config):
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)