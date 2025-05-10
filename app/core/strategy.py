# strategy.py
import pandas as pd
import logging

# Global state variables (to be passed or managed externally)
def check_strategy(df, symbol, active_trade, checked_symbols_state, is_running):
    if df.empty or 'EMA1' not in df.columns:
        logging.warning(f"No valid EMA data for {symbol} in check_strategy")
        return None

    # Only look at the last three candles
    current = df.iloc[-2]  # Just closed candle
    previous = df.iloc[-3]

    ema1_cross = previous['EMA1'] <= previous['EMA3'] and current['EMA1'] > current['EMA3']
    ema2_cross = previous['EMA2'] <= previous['EMA3'] and current['EMA2'] > current['EMA3']

    state = checked_symbols_state.get(symbol, {
        'first_cross': None,
        'second_cross': None,
        'stored_high': None,
    })

    if is_running and not active_trade:
        if state['first_cross'] is None and (ema1_cross or ema2_cross):
            state['first_cross'] = 'EMA1' if ema1_cross else 'EMA2'
            logging.info(f"[{symbol}] First crossover by {state['first_cross']} above EMA3 at {current['timestamp']}")
            checked_symbols_state[symbol] = state
            return None

        if state['first_cross'] and not state['second_cross']:
            if state['first_cross'] == 'EMA1' and ema2_cross:
                state['second_cross'] = 'EMA2'
            elif state['first_cross'] == 'EMA2' and ema1_cross:
                state['second_cross'] = 'EMA1'

            if state['second_cross']:
                state['stored_high'] = current['high']
                logging.info(f"[{symbol}] Second crossover by {state['second_cross']} above EMA3. Stored high: {state['stored_high']}")
                checked_symbols_state[symbol] = state
                return None

        if state['second_cross'] and state['stored_high']:
            if current['close'] > state['stored_high']:
                entry_price = df.iloc[-1]['open']  # Next candle's open
                checked_symbols_state[symbol] = {
                    'first_cross': None,
                    'second_cross': None,
                    'stored_high': None,
                }
                return {'price': entry_price}

    # Reset if no active trade to skip all stale signals
    if not active_trade:
        checked_symbols_state[symbol] = {
            'first_cross': None,
            'second_cross': None,
            'stored_high': None,
        }

    return None

async def exitcondition(df, exit_state):
    if df.empty or 'EMA1' not in df.columns:
        return False

    current_ema1 = df['EMA1'].iloc[-2]
    prev_ema1 = df['EMA1'].iloc[-3]
    current_ema2 = df['EMA2'].iloc[-2]
    prev_ema2 = df['EMA2'].iloc[-3]
    current_ema3 = df['EMA3'].iloc[-2]
    prev_ema3 = df['EMA3'].iloc[-3]
    current_close = df['close'].iloc[-2]
    current_low = df['low'].iloc[-2]

    if exit_state is None:
        exit_state = {
            'first_ema_crossed': False,
            'second_ema_crossed': False,
            'stored_low': None
        }

    # Check for first EMA crossover below EMA3
    ema1_crossed_below = prev_ema1 >= prev_ema3 and current_ema1 < current_ema3
    ema2_crossed_below = prev_ema2 >= prev_ema3 and current_ema2 < current_ema3

    if not exit_state['first_ema_crossed'] and (ema1_crossed_below or ema2_crossed_below):
        exit_state['first_ema_crossed'] = True
        exit_state['second_ema_crossed'] = False
        exit_state['stored_low'] = None
        logging.info(f"First EMA crossed below EMA3")

    # Check for second EMA crossover below EMA3
    if exit_state['first_ema_crossed'] and not exit_state['second_ema_crossed']:
        second_crossed = (ema1_crossed_below and current_ema2 < current_ema3) or (ema2_crossed_below and current_ema1 < current_ema3)
        if second_crossed:
            exit_state['second_ema_crossed'] = True
            exit_state['stored_low'] = current_low
            logging.info(f"Second EMA crossed below EMA3, stored low: {current_low}")

    # Check for close below stored low
    if exit_state['second_ema_crossed'] and exit_state['stored_low'] and current_close < exit_state['stored_low']:
        logging.info(f"Price closed below stored low, exiting long")
        exit_state['first_ema_crossed'] = False
        exit_state['second_ema_crossed'] = False
        exit_state['stored_low'] = None
        return True

    return False