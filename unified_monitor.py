#!/usr/bin/env python3
"""
Hyperliquid Unified Monitor
A unified service that combines scheduled position monitoring with interactive Telegram bot commands.
Provides both automatic updates and on-demand data retrieval with separate logging.
"""

import os
import sys
import time
import json
import logging
import argparse
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor

import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# Load environment variables
load_dotenv()

# Initialize Rich console
console = Console()

class UnifiedHyperliquidMonitor:
    def __init__(self):
        self.wallet_address = os.getenv('HL_WALLET_ADDRESS')
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.refresh_interval = int(os.getenv('REFRESH_INTERVAL_SECONDS', 300))
        self.price_symbols = [s.strip() for s in os.getenv('PRICE_SYMBOLS', 'BTC,ETH,SOL').split(',') if s.strip()]
        
        self.api_base_url = "https://api.hyperliquid.xyz/info"
        self.telegram_api_url = f"https://api.telegram.org/bot{self.telegram_bot_token}"
        
        # Threading control
        self.running = True
        self.bot_thread = None
        
        # Track last Telegram update ID
        self.last_update_id = 0
        
        # Data caching to avoid duplicate API calls
        self.cache_lock = threading.Lock()
        self.cached_positions = None
        self.cached_account_data = None
        self.cached_mark_prices = None
        self.cache_timestamp = 0
        self.cache_duration = 30  # Cache for 30 seconds
        
        # Setup logging
        self.setup_logging()
        
        # Validate configuration
        self.validate_config()
    
    def setup_logging(self):
        """Setup logging with separate files for positions and bot interactions"""
        # Create logs directory
        os.makedirs('logs', exist_ok=True)
        
        # Create timestamped log filenames
        current_time = datetime.now()
        timestamp = current_time.strftime('%Y-%m-%d_%H')
        
        position_log = f"logs/positions_{timestamp}.log"
        bot_log = f"logs/bot_{timestamp}.log"
        main_log = f"logs/main_{timestamp}.log"
        
        # Setup main logger
        self.main_logger = logging.getLogger('main')
        self.main_logger.setLevel(logging.INFO)
        main_handler = logging.FileHandler(main_log, encoding='utf-8')
        main_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.main_logger.addHandler(main_handler)
        self.main_logger.addHandler(RichHandler(console=console, rich_tracebacks=True))
        
        # Setup position logger
        self.position_logger = logging.getLogger('positions')
        self.position_logger.setLevel(logging.INFO)
        pos_handler = logging.FileHandler(position_log, encoding='utf-8')
        pos_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.position_logger.addHandler(pos_handler)
        
        # Setup bot logger
        self.bot_logger = logging.getLogger('bot')
        self.bot_logger.setLevel(logging.INFO)
        bot_handler = logging.FileHandler(bot_log, encoding='utf-8')
        bot_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.bot_logger.addHandler(bot_handler)
        
        self.main_logger.info("🚀 Hyperliquid Unified Monitor started")
        self.position_logger.info("📊 Position monitoring logger initialized")
        self.bot_logger.info("🤖 Bot interaction logger initialized")
    
    def validate_config(self):
        """Validate required environment variables"""
        missing_vars = []
        
        if not self.wallet_address:
            missing_vars.append('HL_WALLET_ADDRESS')
        if not self.telegram_bot_token:
            missing_vars.append('TELEGRAM_BOT_TOKEN')
        if not self.telegram_chat_id:
            missing_vars.append('TELEGRAM_CHAT_ID')
        
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            self.main_logger.error(error_msg)
            console.print(f"❌ {error_msg}", style="bold red")
            sys.exit(1)
        
        self.main_logger.info("✅ Configuration validated successfully")
        self.main_logger.info(f"📊 Configured price symbols: {', '.join(self.price_symbols)}")
    
    def is_cache_valid(self) -> bool:
        """Check if cached data is still valid"""
        return (time.time() - self.cache_timestamp) < self.cache_duration
    
    def get_mark_prices(self, force_refresh: bool = False) -> Dict[str, float]:
        """Fetch all current mark prices from Hyperliquid API with caching"""
        with self.cache_lock:
            if not force_refresh and self.is_cache_valid() and self.cached_mark_prices is not None:
                return self.cached_mark_prices
        
        try:
            payload = {"type": "allMids"}
            
            response = requests.post(self.api_base_url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # The allMids API returns a dictionary with symbol: price_string format
            mids = {}
            if isinstance(data, dict):
                for symbol, price_str in data.items():
                    try:
                        # Skip entries that start with '@' (these are index-based entries)
                        if not symbol.startswith('@'):
                            mids[symbol] = float(price_str)
                    except (ValueError, TypeError):
                        continue
            
            # Update cache
            with self.cache_lock:
                self.cached_mark_prices = mids
                self.cache_timestamp = time.time()
            
            return mids
            
        except Exception as e:
            self.main_logger.error(f"❌ Error fetching mark prices: {e}")
            return {}
    
    def fetch_positions(self, force_refresh: bool = False) -> Optional[List[Dict]]:
        """Fetch perpetual positions from Hyperliquid API with caching"""
        with self.cache_lock:
            if not force_refresh and self.is_cache_valid() and self.cached_positions is not None:
                return self.cached_positions
        
        try:
            payload = {
                "type": "clearinghouseState",
                "user": self.wallet_address
            }
            
            response = requests.post(self.api_base_url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            positions = data.get('assetPositions', []) if data else []
            
            # Filter out zero-size positions and extract active positions
            active_positions = []
            symbols_to_fetch = []
            
            for pos in positions:
                # Extract position data from nested structure
                position_data = pos.get("position", {})
                size = abs(float(position_data.get("szi", 0)))
                
                # Skip zero-size positions (not open)
                if size == 0:
                    continue
                
                side = "LONG" if float(position_data.get("szi", 0)) > 0 else "SHORT"
                coin = position_data.get('coin', 'Unknown')
                symbols_to_fetch.append(coin)
                
                # Extract leverage value from nested structure
                leverage_data = position_data.get("leverage", {})
                leverage_value = leverage_data.get("value", 1) if isinstance(leverage_data, dict) else leverage_data
                
                active_positions.append({
                    "symbol": coin,
                    "side": side,
                    "size": size,
                    "entry_price": float(position_data.get("entryPx", 0)),
                    "mark_price": 0,  # Will be updated below
                    "liq_price": float(position_data.get("liquidationPx", 0)),
                    "unrealized_pnl": float(position_data.get("unrealizedPnl", 0)),
                    "leverage": float(leverage_value),
                    "margin_used": float(position_data.get("marginUsed", 0))
                })
            
            # Fetch mark prices for all symbols
            if symbols_to_fetch:
                mark_prices = self.get_mark_prices()
                
                # Update positions with mark prices
                for pos in active_positions:
                    symbol = pos["symbol"]
                    if symbol in mark_prices:
                        pos["mark_price"] = mark_prices[symbol]
            
            # Update cache
            with self.cache_lock:
                self.cached_positions = active_positions
                if not hasattr(self, 'cache_timestamp') or (time.time() - self.cache_timestamp) > self.cache_duration:
                    self.cache_timestamp = time.time()
            
            return active_positions
            
        except requests.exceptions.RequestException as e:
            self.main_logger.error(f"❌ Failed to fetch positions: {e}")
            return None
        except Exception as e:
            self.main_logger.error(f"❌ Unexpected error fetching positions: {e}")
            return None
    
    def fetch_account_metrics(self, force_refresh: bool = False) -> Optional[Dict]:
        """Fetch account summary from Hyperliquid API with caching"""
        with self.cache_lock:
            if not force_refresh and self.is_cache_valid() and self.cached_account_data is not None:
                return self.cached_account_data
        
        try:
            payload = {
                "type": "clearinghouseState",
                "user": self.wallet_address
            }
            
            response = requests.post(self.api_base_url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            # Extract account data from the response
            account_data = data.get('marginSummary', {}) if data else {}
            
            # Update cache
            with self.cache_lock:
                self.cached_account_data = account_data
                if not hasattr(self, 'cache_timestamp') or (time.time() - self.cache_timestamp) > self.cache_duration:
                    self.cache_timestamp = time.time()
            
            return account_data
            
        except requests.exceptions.RequestException as e:
            self.main_logger.error(f"❌ Failed to fetch account metrics: {e}")
            return None
        except Exception as e:
            self.main_logger.error(f"❌ Unexpected error fetching account metrics: {e}")
            return None
    
    def format_telegram_message(self, positions: List[Dict], account_data: Dict, message_type: str = "scheduled") -> str:
        """Format position and account data into a Telegram message"""
        try:
            # Extract account metrics based on marginSummary response format
            account_value = float(account_data.get('accountValue', 0))
            total_ntl_pos = float(account_data.get('totalNtlPos', 0))
            total_raw_usd = float(account_data.get('totalRawUsd', 0))
            total_margin_used = float(account_data.get('totalMarginUsed', 0))
            
            # Calculate metrics
            cross_margin_ratio = (total_margin_used / account_value * 100) if account_value > 0 else 0
            cross_leverage = (total_ntl_pos / account_value) if account_value > 0 else 0
            
            # Different headers for scheduled vs on-demand
            if message_type == "scheduled":
                header = "🔥 *Hyperliquid Positions Update*"
            else:
                header = "📊 *Hyperliquid Position Summary*"
            
            # Start building message (Markdown format)
            message = f"{header}\n\n"
            
            # Account Summary
            message += "📊 *Account Summary*\n"
            message += f"• Account Equity: ${account_value:,.2f}\n"
            message += f"• Total Raw USD: ${total_raw_usd:,.2f}\n"
            message += f"• Total Notional: ${total_ntl_pos:,.2f}\n"
            message += f"• Margin Used: ${total_margin_used:,.2f}\n"
            message += f"• Cross Margin Ratio: {cross_margin_ratio:.2f}%\n"
            message += f"• Cross Leverage: {cross_leverage:.2f}x\n\n"
            
            # Positions
            if positions:
                message += f"📈 *Open Positions ({len(positions)})*\n\n"
                
                for pos in positions:
                    symbol = pos.get('symbol', 'Unknown')
                    side = pos.get('side', 'Unknown')
                    size = pos.get('size', 0)
                    entry_px = pos.get('entry_price', 0)
                    mark_px = pos.get('mark_price', 0)
                    liq_px = pos.get('liq_price', 0)
                    unrealized_pnl = pos.get('unrealized_pnl', 0)
                    margin_used = pos.get('margin_used', 0)
                    leverage = pos.get('leverage', 1)
                    
                    # Calculate PnL percentage
                    pnl_pct = (unrealized_pnl / (size * entry_px) * 100) if (size * entry_px) > 0 else 0
                    pnl_sign = "+" if unrealized_pnl >= 0 else ""
                    
                    # Color formatting for PnL (green for profit, red for loss)
                    if unrealized_pnl >= 0:
                        pnl_text = f'🟢 *{pnl_sign}${unrealized_pnl:,.2f} ({pnl_sign}{pnl_pct:.2f}%)*'
                    else:
                        pnl_text = f'🔴 *{pnl_sign}${unrealized_pnl:,.2f} ({pnl_sign}{pnl_pct:.2f}%)*'
                    
                    message += f"*{symbol}* ({side.upper()})\n"
                    message += f"• Size: {size:,.4f} {symbol}\n"
                    message += f"• Entry: ${entry_px:,.2f} | Mark: ${mark_px:,.2f}\n"
                    message += f"• Unrealized PnL: {pnl_text}\n"
                    message += f"• Liquidation: ${liq_px:,.2f}\n"
                    message += f"• Margin Required: ${margin_used:,.2f}\n"
                    message += f"• Leverage: {leverage:.1f}x\n\n"
            else:
                message += "📈 *No Open Positions*\n\n"
            
            # Footer
            message += f"🕐 *Updated*: {datetime.now().strftime('%H:%M:%S UTC')}"
            
            return message
            
        except Exception as e:
            self.main_logger.error(f"❌ Error formatting message: {e}")
            return f"❌ Error formatting position data: {str(e)}"
    
    def format_prices_markdown(self, mids: Dict[str, float], symbols: List[str]) -> str:
        """Format token prices in markdown format"""
        try:
            lines = ["📈 *Current Token Prices*\n"]
            
            found_prices = []
            missing_prices = []
            
            for symbol in symbols:
                price = mids.get(symbol)
                if price and price > 0:
                    lines.append(f"• **{symbol}**: ${price:,.2f}")
                    found_prices.append(symbol)
                else:
                    missing_prices.append(symbol)
            
            if not found_prices:
                return "❌ No price data available for configured symbols."
            
            if missing_prices:
                lines.append(f"\n⚠️ *No data for*: {', '.join(missing_prices)}")
            
            lines.append(f"\n🕐 *Updated*: {datetime.now().strftime('%H:%M:%S UTC')}")
            
            return "\n".join(lines)
            
        except Exception as e:
            self.bot_logger.error(f"❌ Error formatting prices: {e}")
            return f"❌ Error formatting price data: {str(e)}"
    
    def send_message(self, message: str, parse_mode: str = "Markdown", reply_markup: dict = None) -> bool:
        """Send message to Telegram"""
        try:
            url = f"{self.telegram_api_url}/sendMessage"
            
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            if reply_markup:
                payload['reply_markup'] = reply_markup
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            return True
            
        except requests.exceptions.RequestException as e:
            self.main_logger.error(f"❌ Failed to send Telegram message: {e}")
            return False
        except Exception as e:
            self.main_logger.error(f"❌ Unexpected error sending message: {e}")
            return False
    
    def send_inline_command_menu(self) -> bool:
        """Send inline keyboard with command buttons"""
        try:
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "📈 Prices", "callback_data": "/prices"},
                        {"text": "📊 Position", "callback_data": "/position"},
                    ],
                    [
                        {"text": "ℹ️ Help", "callback_data": "/help"}
                    ]
                ]
            }
            
            message = f"""
🤖 *Hyperliquid Bot Menu*

Welcome! Use the buttons below to interact with your Hyperliquid account:

📈 *Prices* - Get current token prices
📊 *Position* - View positions and account summary  
ℹ️ *Help* - Show detailed help information

👇 *Select a command:*
            """.strip()
            
            success = self.send_message(message, reply_markup=keyboard)
            
            if success:
                self.bot_logger.info("✅ Inline command menu sent successfully")
            else:
                self.bot_logger.error("❌ Failed to send inline command menu")
            
            return success
            
        except Exception as e:
            self.bot_logger.error(f"❌ Error sending inline command menu: {e}")
            return False
    
    def display_console_summary(self, positions: List[Dict], account_data: Dict):
        """Display a summary in the console"""
        try:
            # Account summary table
            account_table = Table(title="Account Summary", show_header=True, header_style="bold magenta")
            account_table.add_column("Metric", style="cyan")
            account_table.add_column("Value", style="green")
            
            # Extract account metrics based on marginSummary response format
            account_value = float(account_data.get('accountValue', 0))
            total_ntl_pos = float(account_data.get('totalNtlPos', 0))
            total_raw_usd = float(account_data.get('totalRawUsd', 0))
            total_margin_used = float(account_data.get('totalMarginUsed', 0))
            
            # Calculate metrics
            cross_margin_ratio = (total_margin_used / account_value * 100) if account_value > 0 else 0
            cross_leverage = (total_ntl_pos / account_value) if account_value > 0 else 0
            
            account_table.add_row("Account Equity", f"${account_value:,.2f}")
            account_table.add_row("Total Raw USD", f"${total_raw_usd:,.2f}")
            account_table.add_row("Total Notional", f"${total_ntl_pos:,.2f}")
            account_table.add_row("Margin Used", f"${total_margin_used:,.2f}")
            account_table.add_row("Cross Leverage", f"{cross_leverage:.2f}x")
            
            console.print(account_table)
            
            # Positions table
            if positions:
                pos_table = Table(title=f"Open Positions ({len(positions)})", show_header=True, header_style="bold magenta")
                pos_table.add_column("Symbol", style="cyan")
                pos_table.add_column("Side", style="yellow")
                pos_table.add_column("Size", style="white")
                pos_table.add_column("Entry Price", style="white")
                pos_table.add_column("Mark Price", style="white")
                pos_table.add_column("Unrealized PnL", style="green")
                pos_table.add_column("Leverage", style="blue")
                
                for pos in positions:
                    symbol = pos.get('symbol', 'Unknown')
                    side = pos.get('side', 'Unknown')
                    size = pos.get('size', 0)
                    entry_px = pos.get('entry_price', 0)
                    mark_px = pos.get('mark_price', 0)
                    unrealized_pnl = pos.get('unrealized_pnl', 0)
                    leverage = pos.get('leverage', 1)
                    
                    pnl_color = "green" if unrealized_pnl >= 0 else "red"
                    pnl_sign = "+" if unrealized_pnl >= 0 else ""
                    
                    pos_table.add_row(
                        symbol,
                        side.upper(),
                        f"{size:,.4f}",
                        f"${entry_px:,.2f}",
                        f"${mark_px:,.2f}",
                        f"[{pnl_color}]{pnl_sign}${unrealized_pnl:,.2f}[/{pnl_color}]",
                        f"{leverage:.1f}x"
                    )
                
                console.print(pos_table)
            else:
                console.print(Panel("No open positions", title="Positions", style="yellow"))
                
        except Exception as e:
            self.main_logger.error(f"❌ Error displaying console summary: {e}")
    
    # Bot command handlers
    def get_updates(self) -> List[Dict]:
        """Get updates from Telegram"""
        try:
            url = f"{self.telegram_api_url}/getUpdates"
            
            params = {
                'offset': self.last_update_id + 1,
                'timeout': 10,
                'limit': 100
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('ok'):
                return data.get('result', [])
            else:
                self.bot_logger.error(f"❌ Telegram API error: {data}")
                return []
                
        except requests.exceptions.RequestException as e:
            self.bot_logger.error(f"❌ Failed to get Telegram updates: {e}")
            return []
        except Exception as e:
            self.bot_logger.error(f"❌ Unexpected error getting updates: {e}")
            return []
    
    def handle_prices_command(self):
        """Handle /prices command"""
        self.bot_logger.info("💰 Processing /prices command...")
        
        # Get current mark prices
        mids = self.get_mark_prices()
        
        if not mids:
            error_msg = "❌ Unable to fetch price data from Hyperliquid API"
            self.send_message(error_msg)
            return
        
        # Format and send prices
        message = self.format_prices_markdown(mids, self.price_symbols)
        success = self.send_message(message)
        
        if success:
            self.bot_logger.info("✅ Prices command completed successfully")
        else:
            self.bot_logger.error("❌ Failed to send prices message")
    
    def handle_position_command(self):
        """Handle /position command"""
        self.bot_logger.info("📊 Processing /position command...")
        
        if not self.wallet_address:
            error_msg = "❌ Wallet address not configured. Please set HL_WALLET_ADDRESS in your environment."
            self.send_message(error_msg)
            return
        
        # Fetch data (use cache if available)
        positions = self.fetch_positions()
        account_data = self.fetch_account_metrics()
        
        if positions is None or account_data is None:
            error_msg = "❌ Unable to fetch position data from Hyperliquid API"
            self.send_message(error_msg)
            return
        
        # Format and send positions
        message = self.format_telegram_message(positions, account_data, "on-demand")
        success = self.send_message(message)
        
        if success:
            self.bot_logger.info("✅ Position command completed successfully")
        else:
            self.bot_logger.error("❌ Failed to send position message")
    
    def handle_help_command(self):
        """Handle /help command"""
        help_text = f"""
🤖 *Hyperliquid Bot Commands*

• `/prices` - Get current token prices
• `/position` - Get current positions and account summary
• `/help` - Show this help message

📊 *Configured Price Symbols*:
{', '.join(self.price_symbols)}

🔄 *Scheduled Updates*: Every {self.refresh_interval} seconds

💡 *Note*: This bot provides both scheduled updates and on-demand data from your Hyperliquid account.
        """.strip()
        
        success = self.send_message(help_text)
        if success:
            self.bot_logger.info("✅ Help command completed successfully")
        else:
            self.bot_logger.error("❌ Failed to send help message")
    
    def answer_callback_query(self, callback_query_id: str, text: str = "") -> bool:
        """Answer callback query to remove loading state"""
        try:
            url = f"{self.telegram_api_url}/answerCallbackQuery"
            
            payload = {
                'callback_query_id': callback_query_id,
                'text': text
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            return True
            
        except Exception as e:
            self.bot_logger.error(f"❌ Error answering callback query: {e}")
            return False
    
    def process_callback_query(self, callback_query: Dict):
        """Process inline button callback"""
        try:
            callback_data = callback_query.get('data', '')
            callback_id = callback_query.get('id', '')
            user = callback_query.get('from', {})
            username = user.get('username', user.get('first_name', 'Unknown'))
            
            self.bot_logger.info(f"🔘 Received callback from {username}: {callback_data}")
            
            # Answer the callback query first to remove loading state
            self.answer_callback_query(callback_id)
            
            # Process the command
            if callback_data == '/prices':
                self.handle_prices_command()
            elif callback_data == '/position':
                self.handle_position_command()
            elif callback_data == '/help':
                self.handle_help_command()
            else:
                self.bot_logger.warning(f"❓ Unknown callback data: {callback_data}")
                
        except Exception as e:
            self.bot_logger.error(f"❌ Error processing callback query: {e}")
    
    def process_message(self, message: Dict):
        """Process incoming message"""
        try:
            # Extract message text
            text = message.get('text', '').strip().lower()
            
            # Extract user info for logging
            user = message.get('from', {})
            username = user.get('username', user.get('first_name', 'Unknown'))
            
            self.bot_logger.info(f"📨 Received message from {username}: {text}")
            
            # Handle commands
            if text == '/prices':
                self.handle_prices_command()
            elif text == '/position' or text == '/positions':
                self.handle_position_command()
            elif text == '/start':
                self.send_inline_command_menu()
            elif text == '/help':
                self.handle_help_command()
            else:
                # Unknown command
                response = f"❓ Unknown command: `{text}`\n\nSend `/help` for available commands."
                self.send_message(response)
                self.bot_logger.info(f"❓ Unknown command received: {text}")
                
        except Exception as e:
            self.bot_logger.error(f"❌ Error processing message: {e}")
            error_msg = "❌ Error processing your request. Please try again."
            self.send_message(error_msg)
    
    def bot_loop(self):
        """Bot message processing loop (runs in separate thread)"""
        self.bot_logger.info("🤖 Bot message loop started")
        
        while self.running:
            try:
                # Get updates from Telegram
                updates = self.get_updates()
                
                for update in updates:
                    # Update last processed update ID
                    self.last_update_id = max(self.last_update_id, update.get('update_id', 0))
                    
                    # Process message if it exists
                    if 'message' in update:
                        message = update['message']
                        
                        # Only process text messages
                        if 'text' in message:
                            self.process_message(message)
                    
                    # Process callback query if it exists (inline button clicks)
                    elif 'callback_query' in update:
                        callback_query = update['callback_query']
                        self.process_callback_query(callback_query)
                
                # Small delay to avoid hammering the API
                time.sleep(1)
                
            except Exception as e:
                self.bot_logger.error(f"❌ Error in bot loop: {e}")
                time.sleep(5)  # Wait before retrying
        
        self.bot_logger.info("🤖 Bot message loop stopped")
    
    def run_position_update(self) -> bool:
        """Run a single position update cycle"""
        try:
            self.position_logger.info("📡 Starting scheduled position update...")
            
            # Fetch data (force refresh for scheduled updates)
            positions = self.fetch_positions(force_refresh=True)
            account_data = self.fetch_account_metrics(force_refresh=True)
            
            if positions is None or account_data is None:
                self.position_logger.error("❌ Failed to fetch required data")
                return False
            
            # Display console summary
            self.display_console_summary(positions, account_data)
            
            # Format and send message
            message = self.format_telegram_message(positions, account_data, "scheduled")
            success = self.send_message(message)
            
            if success:
                self.position_logger.info("✅ Scheduled update completed successfully")
                console.print("✅ Update completed successfully", style="bold green")
            else:
                self.position_logger.error("❌ Failed to send scheduled update")
                console.print("❌ Failed to send Telegram message", style="bold red")
            
            return success
            
        except Exception as e:
            self.position_logger.error(f"❌ Error in position update: {e}")
            return False
    
    def main_loop(self, run_once: bool = False):
        """Main application loop"""
        try:
            console.print(Panel.fit(
                "🚀 Hyperliquid Unified Monitor\n"
                f"Wallet: {self.wallet_address[:10]}...\n"
                f"Refresh: {self.refresh_interval}s\n"
                f"Bot Commands: /prices, /position, /help",
                title="Starting Unified Monitor",
                style="bold blue"
            ))
            
            # Start bot thread
            if not run_once:
                self.bot_thread = threading.Thread(target=self.bot_loop, daemon=True)
                self.bot_thread.start()
                console.print("🤖 [bold green]Telegram Bot Started[/bold green]")
                console.print(f"📊 Monitoring symbols: {', '.join(self.price_symbols)}")
                console.print("💡 Send /prices to get current token prices")
                console.print("📊 Send /position to get current positions and account summary")
            
            iteration = 0
            
            while True:
                iteration += 1
                
                console.print(f"\n🔄 [bold cyan]Update #{iteration}[/bold cyan] - {datetime.now().strftime('%H:%M:%S')}")
                
                success = self.run_position_update()
                
                if run_once:
                    break
                
                if success:
                    console.print(f"⏰ Next update in {self.refresh_interval} seconds...")
                    time.sleep(self.refresh_interval)
                else:
                    console.print("⚠️ Retrying in 60 seconds due to error...", style="yellow")
                    time.sleep(60)
                    
        except KeyboardInterrupt:
            console.print("\n👋 Shutting down gracefully...", style="bold yellow")
            self.running = False
            if self.bot_thread and self.bot_thread.is_alive():
                self.bot_thread.join(timeout=5)
            self.main_logger.info("Application stopped by user")
        except Exception as e:
            self.main_logger.error(f"❌ Fatal error in main loop: {e}")
            console.print(f"❌ Fatal error: {e}", style="bold red")
            self.running = False

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Hyperliquid Unified Monitor")
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    args = parser.parse_args()
    
    monitor = UnifiedHyperliquidMonitor()
    monitor.main_loop(run_once=args.once)

if __name__ == "__main__":
    main()
