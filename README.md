# Hyperliquid Position Monitor

A Python CLI tool that connects to Hyperliquid using a wallet API key, fetches detailed perpetual position and account data, and sends updates to a Telegram bot with configurable refresh intervals.

## 🚀 Features

- **Real-time Position Monitoring**: Fetch live perpetual positions from Hyperliquid
- **Account Metrics**: Track account equity, margin usage, leverage, and PnL
- **Telegram Integration**: Receive formatted updates via Telegram bot
- **On-Demand Price Lookup**: `/prices` command for instant token price checks
- **On-Demand Position Updates**: `/position` command for instant position and account summary
- **Interactive Telegram Bot**: Responds to commands and provides help
- **Automated Setup**: One-command setup with virtual environment management
- **Rich Console Output**: Beautiful terminal interface with tables and colors
- **Comprehensive Logging**: Dual logging (console + hourly log files)
- **Configurable Refresh**: Set custom update intervals
- **Graceful Shutdown**: Clean exit with Ctrl+C

## 📋 Requirements

- Python 3.7+
- Internet connection
- Hyperliquid wallet address
- Telegram bot token and chat ID

## 🛠️ Quick Start

### 1. Clone or Download

Download the project files to your local machine.

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
# Hyperliquid Configuration
HL_WALLET_KEY=your_hyperliquid_wallet_address

# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Application Configuration
REFRESH_INTERVAL_SECONDS=300
```

### 3. Run the Application

**Automated Setup & Launch:**
```bash
python start.py
```

This will:
- Create virtual environment (if needed)
- Install dependencies
- Validate configuration
- Test connectivity
- Launch the unified monitor

**Manual Launch (after setup):**
```bash
python unified_monitor.py
```

**Run Once (no continuous monitoring):**
```bash
python unified_monitor.py --once
```

**Interactive Bot Only:**
```bash
python telegram_bot.py
```

## 📊 Data Tracked

### Position Information
- Symbol (e.g., BTC, ETH)
- Side (LONG/SHORT)
- Position Size
- Entry Price
- Current Mark Price
- Liquidation Price
- Unrealized PnL ($ and %)
- Margin Required

### Account Metrics
- Account Equity
- Total Raw USD
- Total Notional Position
- Margin Used
- Cross Margin Ratio
- Cross Account Leverage

## 📱 Telegram Setup

### 🤖 How to Set Up Your Telegram Bot and Get Chat ID

Follow these steps to create your Telegram bot and retrieve your chat ID.

---

#### 1. Create a Telegram Bot

1. Open the Telegram app and search for [@BotFather](https://t.me/BotFather).
2. Start a chat and send the command:

   ```
   /newbot
   ```
3. Follow the prompts to:

   * Set a **name** for your bot.
   * Set a **username** (must end in `bot`, e.g., `MyNotifierBot`).
4. BotFather will respond with a **token** like this:

   ```
   Use this token to access the HTTP API:
   123456789:ABCdefGhiJKlmNOPQRsTUVwxyZ
   ```

✅ Copy this and set it as your `TELEGRAM_BOT_TOKEN` in the `.env` file.

---

#### 2. Get Your Chat ID

To get the `TELEGRAM_CHAT_ID`:

1. Open a chat with your new bot (search for it by username) and click **Start**.

2. Send any message to the bot (e.g., "Hi").

3. Open this URL in a browser, replacing `<BOT_TOKEN>` with your bot token:

   ```
   https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
   ```

   Example:

   ```
   https://api.telegram.org/bot123456789:ABCdefGhiJKlmNOPQRsTUVwxyZ/getUpdates
   ```

4. Look for a JSON response like:

   ```json
   {
     "message": {
       "chat": {
         "id": 987654321,
         "first_name": "YourName",
         ...
       },
       ...
     }
   }
   ```

5. Copy the numeric `id` under `"chat"` — this is your `TELEGRAM_CHAT_ID`.

✅ Add it to your `.env` file.

---

#### ✅ Example `.env` file

```env
# Hyperliquid Configuration
HL_WALLET_ADDRESS=your_hyperliquid_wallet_address

# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Application Configuration
REFRESH_INTERVAL_SECONDS=300
```

You're now ready to send messages from your Python app to Telegram! 🚀

## 🔧 Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HL_WALLET_ADDRESS` | Hyperliquid wallet address | Required |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | Required |
| `TELEGRAM_CHAT_ID` | Telegram chat ID | Required |
| `REFRESH_INTERVAL_SECONDS` | Update frequency | 300 (5 minutes) |
| `PRICE_SYMBOLS` | Comma-separated list of tokens for `/prices` command | BTC,ETH,SOL |

### Command Line Options

```bash
python send_positions.py --help
```

- `--once`: Run once and exit (ignore refresh interval)

## 📁 Project Structure

```
hyperliquid-position/
├── start.py              # Automated setup and launch script
├── unified_monitor.py    # Main unified service (scheduled + bot commands)
├── send_positions.py     # Legacy CLI application (scheduled only)
├── telegram_bot.py       # Legacy interactive bot (commands only)
├── requirements.txt      # Python dependencies
├── .env                 # Environment variables (your config)
├── .env.example         # Template for environment variables
├── logs/                # Log files (auto-created)
│   ├── main_YYYY-MM-DD_HH.log      # Main application logs
│   ├── positions_YYYY-MM-DD_HH.log # Position monitoring logs
│   └── bot_YYYY-MM-DD_HH.log       # Bot interaction logs
├── venv/                # Virtual environment (auto-created)
└── README.md            # This file
```

## 📝 Logging

### Console Output
- Real-time colored logs
- Rich formatted tables
- Progress indicators
- Error highlighting

### File Logging (Unified Monitor)
- **Main Application**: `logs/main_2025-01-03_14.log`
  - Application lifecycle, configuration, errors
- **Position Monitoring**: `logs/positions_2025-01-03_14.log`
  - Scheduled position updates, API calls, data processing
- **Bot Interactions**: `logs/bot_2025-01-03_14.log`
  - Telegram command processing, user interactions

### File Logging (Legacy Applications)
- **send_positions.py**: `logs/app_2025-01-03_14.log`
- **telegram_bot.py**: Standard console logging

### Log Levels
- `INFO`: Normal operations, API calls, Telegram sends
- `DEBUG`: Detailed API responses, data processing
- `WARNING`: Retry attempts, minor issues
- `ERROR`: API failures, critical errors

## 🔄 Usage Examples

### Continuous Monitoring
```bash
python start.py
```
Runs indefinitely, sending updates every 5 minutes (or your configured interval).

### One-time Check
```bash
python send_positions.py --once
```
Fetches current data, sends to Telegram, and exits.

### Custom Refresh Interval
Set `REFRESH_INTERVAL_SECONDS=60` in `.env` for 1-minute updates.

### Interactive Telegram Bot
```bash
python telegram_bot.py
```
Runs the interactive Telegram bot that responds to commands:
- `/prices` - Get current token prices for configured symbols
- `/help` - Show available commands and configuration
- `/start` - Same as `/help`

## 🤖 Telegram Bot Commands

### Interactive Inline Buttons

When you send `/start` to the bot, you'll receive an interactive menu with clickable buttons:

```
🤖 Hyperliquid Bot Menu

Welcome! Use the buttons below to interact with your Hyperliquid account:

📈 Prices - Get current token prices
📊 Position - View positions and account summary  
ℹ️ Help - Show detailed help information

👇 Select a command:

[📈 Prices] [📊 Position]
      [ℹ️ Help]
```

**How to Use:**
- Send `/start` to get the interactive menu
- Click any button to execute the corresponding command
- No need to type commands manually!

### `/prices` Command
Get instant price updates for your configured tokens:

**Example Response:**
```
📈 Current Token Prices

• BTC: $114,023.50
• ETH: $3,490.35
• SOL: $162.12
• AVAX: $21.40
• MATIC: $0.38
• DOGE: $0.20
• ADA: $0.73
• DOT: $3.59
• LINK: $16.30
• UNI: $9.16

🕐 Updated: 12:07:40 UTC
```

**Configuration:**
Add `PRICE_SYMBOLS` to your `.env` file to customize which tokens to track:
```env
PRICE_SYMBOLS=BTC,ETH,SOL,AVAX,MATIC,DOGE,ADA,DOT,LINK,UNI
```

### `/position` Command
Get instant position and account summary updates:

**Example Response:**
```
🔥 Hyperliquid Positions Update

📊 Account Summary
• Account Equity: $3,085.52
• Total Raw USD: $-44,903.61
• Total Notional: $47,989.14
• Margin Used: $2,202.65
• Cross Leverage: 15.55x

📈 Open Positions (2)

ETH (LONG)
• Size: 5.6700 ETH
• Entry: $3,486.34 | Mark: $3,470.00
• Unrealized PnL: 🔴 -$87.59 (-0.44%)
• Liquidation: $3,122.30
• Margin Required: $1,200.00
• Leverage: 25.0x

SOL (LONG)
• Size: 175.0000 SOL
• Entry: $163.46 | Mark: $161.75
• Unrealized PnL: 🔴 -$300.03 (-1.05%)
• Liquidation: $150.57
• Margin Required: $1,002.65
• Leverage: 20.0x

🕐 Updated: 12:12:30 UTC
```

### `/help` Command
Shows available commands and current configuration.

### Available Commands Summary
- **`/start`** - Show interactive button menu (recommended)
- **`/prices`** - Get current token prices
- **`/position`** - Get positions and account summary
- **`/help`** - Show help information

**💡 Pro Tip:** Use `/start` for the easiest interaction with inline buttons!

## 📤 Telegram Message Format

```
🔥 Hyperliquid Positions Update

📊 Account Summary
• Account Equity: $12,450.67
• Total Raw USD: $11,200.00
• Total Notional: $25,000.00
• Margin Used: $1,250.00
• Cross Margin Ratio: 10.04%
• Cross Leverage: 2.01x

📈 Open Positions (2)

BTC (LONG)
• Size: 0.5000 BTC
• Entry: $45,200.00 | Mark: $46,100.00
• Unrealized PnL: +$450.00 (+1.99%)
• Liquidation: $38,500.00
• Margin Used: $750.00

ETH (SHORT)
• Size: 5.0000 ETH
• Entry: $3,200.00 | Mark: $3,150.00
• Unrealized PnL: +$250.00 (+1.56%)
• Liquidation: $3,850.00
• Margin Used: $500.00

🕐 Updated: 2025-01-03 14:30:15 UTC
```

## 🛡️ Error Handling

- **API Failures**: Automatic retry with exponential backoff
- **Network Issues**: Graceful degradation and retry logic
- **Invalid Data**: Comprehensive validation and error reporting
- **Telegram Failures**: Retry mechanism for message delivery
- **Configuration Errors**: Clear error messages and validation

## 🔧 Troubleshooting

### Common Issues

**"Missing environment variables"**
- Ensure `.env` file exists and contains all required variables
- Check that values don't contain placeholder text like `your_wallet_address`

**"Failed to fetch positions"**
- Verify wallet address is correct
- Check internet connectivity
- Ensure Hyperliquid API is accessible

**"Failed to send Telegram message"**
- Verify bot token and chat ID are correct
- Ensure you've started a conversation with the bot
- Check Telegram API accessibility

**"Python not found"**
- Install Python 3.7+ from [python.org](https://python.org)
- Ensure Python is added to your system PATH

### Debug Mode

For detailed debugging, check the log files in the `logs/` directory. They contain comprehensive information about API calls, responses, and any errors.

## 🤝 Contributing

Feel free to submit issues, feature requests, or pull requests to improve this tool.

## 📄 License

This project is open source and available under the MIT License.

## ⚠️ Disclaimer

This tool is for informational purposes only. Always verify position data directly on the Hyperliquid platform. The authors are not responsible for any trading decisions made based on this tool's output.
