ema-long-trading-bot/
│
├── strategy.py
├── trading.py
├── indicators.py
├── telegram_ui.py
├── time_utils.py
├── logger.py
├── main.py
├── config.json  # The file you requested, placed here
├── README.md
└── .gitignore

# EMA Long Trading Bot

A Python-based trading bot for Binance futures that uses an EMA crossover strategy to execute long positions. The bot integrates with Telegram for notifications and control.

## Features
- **EMA Crossover Strategy**: Uses three EMAs (short, medium, long) to identify entry and exit points.
- **Telegram Integration**: Start/stop the bot, check balance, view trades, and adjust settings via Telegram.
- **Configurable Parameters**: Adjust EMA periods, take-profit, stop-loss, leverage, and more through a config file or Telegram commands.
- **Time-Based Exits**: Option to exit trades after a specified duration.
- **Error Handling**: Retries for failed API calls and logging for debugging.

## Project Structure
- `strategy.py`: Contains the trading strategy logic (`check_strategy`, `exitcondition`).
- `trading.py`: Handles trade execution and position management.
- `indicators.py`: Calculates technical indicators (EMA, SMA).
- `telegram_ui.py`: Manages Telegram UI and command handlers.
- `time_utils.py`: Time-related utilities (e.g., syncing with Binance, waiting for candle close).
- `logger.py`: Sets up logging configuration.
- `main.py`: Entry point of the bot, ties everything together.
- `config.json`: Configuration file for API keys, trading pairs, and parameters.

## Setup Instructions

### Prerequisites
- Python 3.8+
- Binance account with futures enabled
- Telegram bot token and chat ID

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ema-long-trading-bot.git
   cd ema-long-trading-bot