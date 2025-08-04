# Hyperliquid Position Monitor

A modular Python application for monitoring Hyperliquid trading positions with real-time Telegram notifications and rich console output.

## 🚀 Features

- **Real-time Position Monitoring**: Track your Hyperliquid positions with automatic updates
- **Telegram Bot Integration**: Interactive bot with command support and inline keyboards
- **Rich Console Output**: Beautiful terminal interface with tables and colored output
- **Smart Caching**: Efficient data caching to reduce API calls
- **Intelligent Alerts**: Smart notifications for position changes and significant P&L movements
- **Comprehensive Error Handling**: Robust error handling and recovery mechanisms

## 📋 Requirements

- Python 3.8+
- Hyperliquid account with API access
- Telegram Bot Token
- Telegram Chat ID

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/satishjaiswal/hyperliquid-position.git
   cd hyperliquid-position
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your actual values:
   ```env
   HL_WALLET_ADDRESS=your_hyperliquid_wallet_address
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   TELEGRAM_CHAT_ID=your_telegram_chat_id
   REFRESH_INTERVAL_SECONDS=300
   PRICE_SYMBOLS=BTC,ETH,SOL
   API_TIMEOUT=30
   CACHE_DURATION=30
   LOG_LEVEL=INFO
   LOG_DIRECTORY=logs
   ```

## 🚀 Usage

### Quick Start (Recommended)

For first-time setup or if you want automatic environment management:

```bash
python start.py
```

The start script will:
1. Check Python version compatibility
2. Clear old log files
3. Create virtual environment if needed
4. Install/upgrade dependencies
5. Validate environment configuration
6. Start the application

### Manual Running

If you have already set up the environment:

```bash
python run.py
```

The application will:
1. Validate your environment configuration
2. Test connectivity to Hyperliquid and Telegram APIs
3. Start the position monitor and Telegram bot
4. Send periodic updates and respond to commands

### Telegram Commands

- `/start` or `/menu` - Show interactive command menu
- `/position` - View current positions and account summary
- `/prices` - Get current token prices
- `/fills` - View recent order fills
- `/openorders` - View current open orders
- `/help` - Show help information
- `/status` - Check system status

### Interactive Features

The Telegram bot includes an interactive inline keyboard for easy access to all commands without typing.

## 📁 Project Structure

```
hyperliquid-position/
├── src/                          # Source code
│   ├── main.py                   # Main application entry point
│   ├── config/                   # Configuration management
│   │   ├── settings.py           # Application settings
│   │   ├── environment.py        # Environment validation
│   │   └── logging_config.py     # Logging configuration
│   ├── models/                   # Data models
│   │   ├── position.py           # Position data model
│   │   ├── account.py            # Account summary model
│   │   ├── order.py              # Order and fill models
│   │   └── price.py              # Price data model
│   ├── services/                 # Business logic services
│   │   ├── hyperliquid_api.py    # Hyperliquid API service
│   │   ├── telegram_service.py   # Telegram API service
│   │   ├── cache_service.py      # Caching service
│   │   └── position_service.py   # Position business logic
│   ├── formatters/               # Output formatters
│   │   ├── telegram_formatter.py # Telegram message formatting
│   │   └── console_formatter.py  # Console output formatting
│   ├── bot/                      # Bot components
│   │   └── telegram_bot.py       # Telegram bot handler
│   └── monitor/                  # Monitoring components
│       └── position_monitor.py   # Position monitoring logic
├── logs/                         # Log files (auto-created)
├── start.py                      # Automated setup and startup script
├── run.py                        # Application entry point
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment template
└── README.md                     # This file
```

## 🏗️ Architecture

The application follows a clean, modular architecture:

- **Configuration Layer**: Manages settings and environment validation
- **Data Models**: Type-safe data structures for all entities
- **Service Layer**: Business logic and external API integrations
- **Formatters**: Output formatting for different channels
- **Bot Layer**: User interaction handling
- **Monitor Layer**: Automated monitoring and alerting

## 📊 Monitoring Features

### Automatic Alerts

The monitor sends intelligent alerts for:
- **New Positions**: When new positions are opened
- **Closed Positions**: When positions are closed with P&L summary
- **Significant P&L Changes**: When positions change by >$100 or >5%
- **Periodic Updates**: Hourly position summaries

### Console Output

Rich terminal interface with:
- Real-time position tables
- Account summary panels
- Colored P&L indicators
- Progress indicators and status messages

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HL_WALLET_ADDRESS` | Your Hyperliquid wallet address | Required |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from @BotFather | Required |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID | Required |
| `REFRESH_INTERVAL_SECONDS` | Update interval in seconds | 300 |
| `PRICE_SYMBOLS` | Comma-separated price symbols | BTC,ETH,SOL |
| `API_TIMEOUT` | API request timeout in seconds | 30 |
| `CACHE_DURATION` | Cache TTL in seconds | 30 |
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | INFO |
| `LOG_DIRECTORY` | Log file directory | logs |

## 🐛 Troubleshooting

### Common Issues

1. **Environment Validation Fails**:
   - Check your `.env` file has all required variables
   - Ensure no placeholder values remain

2. **API Connection Issues**:
   - Verify your wallet address is correct
   - Check your internet connection
   - Ensure Hyperliquid API is accessible

3. **Telegram Bot Not Responding**:
   - Verify bot token is correct
   - Check chat ID is accurate
   - Ensure bot has been started with `/start`

### Debug Mode

Enable debug logging:
```env
LOG_LEVEL=DEBUG
```

This provides detailed information about API requests, cache operations, and internal state changes.

## 🔒 Security

- **Environment Variables**: Sensitive data stored in environment
- **Chat ID Validation**: Only authorized users can interact
- **API Rate Limiting**: Respectful API usage patterns
- **Error Sanitization**: No sensitive data in error messages

## 📈 Performance

- **Smart Caching**: Reduces API calls by up to 80%
- **Async Operations**: Non-blocking I/O for better performance
- **Memory Efficient**: Minimal memory footprint
- **Resource Cleanup**: Proper resource management and cleanup

## ⚠️ Disclaimer

This software is for educational and informational purposes only. Use at your own risk. The authors are not responsible for any financial losses or damages resulting from the use of this software.

---

**Happy Trading! 📈**
