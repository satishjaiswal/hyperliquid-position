#!/usr/bin/env python3
"""
Hyperliquid Telegram Bot
A Telegram bot that responds to commands for Hyperliquid data.
Supports /prices command for on-demand token price lookups.
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv
from rich.console import Console

# Load environment variables
load_dotenv()

# Initialize Rich console
console = Console()

class HyperliquidTelegramBot:
    def __init__(self):
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.wallet_address = os.getenv('HL_WALLET_ADDRESS')
        self.price_symbols = [s.strip() for s in os.getenv('PRICE_SYMBOLS', 'BTC,ETH,SOL').split(',') if s.strip()]
        
        self.api_base_url = "https://api.hyperliquid.xyz/info"
        self.telegram_api_url = f"https://api.telegram.org/bot{self.telegram_bot_token}"
        
        # Setup logging
        self.setup_logging()
        
        # Validate configuration
        self.validate_config()
        
        # Track last update ID to avoid processing duplicate messages
        self.last_update_id = 0
    
    def setup_logging(self):
        """Setup logging with console output"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("🤖 Hyperliquid Telegram Bot started")
    
    def validate_config(self):
        """Validate required environment variables"""
        missing_vars = []
        
        if not self.telegram_bot_token:
            missing_vars.append('TELEGRAM_BOT_TOKEN')
        if not self.telegram_chat_id:
            missing_vars.append('TELEGRAM_CHAT_ID')
        
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            self.logger.error(error_msg)
            console.print(f"❌ {error_msg}", style="bold red")
            sys.exit(1)
        
        self.logger.info("✅ Bot configuration validated successfully")
        self.logger.info(f"📊 Configured price symbols: {', '.join(self.price_symbols)}")
    
    def get_mark_prices(self) -> Dict[str, float]:
        """Fetch all current mark prices from Hyperliquid API"""
        try:
            payload = {"type": "allMids"}
            
            self.logger.info("📡 Fetching mark prices from Hyperliquid API...")
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
            
            self.logger.info(f"✅ Fetched {len(mids)} token prices")
            return mids
            
        except Exception as e:
            self.logger.error(f"❌ Error fetching mark prices: {e}")
            return {}
    
    def fetch_positions(self) -> Optional[List[Dict]]:
        """Fetch perpetual positions from Hyperliquid API"""
        try:
            payload = {
                "type": "clearinghouseState",
                "user": self.wallet_address
            }
            
            self.logger.info("📡 Fetching positions from Hyperliquid API...")
            response = requests.post(self.api_base_url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            positions = data.get('assetPositions', []) if data else []
            
            self.logger.info(f"✅ Found {len(positions)} positions in API response")
            
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
                self.logger.info("📡 Fetching current mark prices...")
                mark_prices = self.get_mark_prices()
                
                # Update positions with mark prices
                for pos in active_positions:
                    symbol = pos["symbol"]
                    if symbol in mark_prices:
                        pos["mark_price"] = mark_prices[symbol]
            
            self.logger.info(f"✅ Successfully fetched {len(active_positions)} active positions")
            
            return active_positions
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Failed to fetch positions: {e}")
            return None
        except Exception as e:
            self.logger.error(f"❌ Unexpected error fetching positions: {e}")
            return None
    
    def fetch_account_metrics(self) -> Optional[Dict]:
        """Fetch account summary from Hyperliquid API"""
        try:
            payload = {
                "type": "clearinghouseState",
                "user": self.wallet_address
            }
            
            self.logger.info("📊 Fetching account metrics from Hyperliquid API...")
            response = requests.post(self.api_base_url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            # Extract account data from the response
            account_data = data.get('marginSummary', {}) if data else {}
            self.logger.info("✅ Successfully fetched account metrics")
            
            return account_data
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Failed to fetch account metrics: {e}")
            return None
        except Exception as e:
            self.logger.error(f"❌ Unexpected error fetching account metrics: {e}")
            return None
    
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
            self.logger.error(f"❌ Error formatting prices: {e}")
            return f"❌ Error formatting price data: {str(e)}"
    
    def format_positions_markdown(self, positions: List[Dict], account_data: Dict) -> str:
        """Format position and account data into a Telegram message"""
        try:
            # Extract account metrics based on marginSummary response format
            account_value = float(account_data.get('accountValue', 0))
            total_ntl_pos = float(account_data.get('totalNtlPos', 0))
            total_raw_usd = float(account_data.get('totalRawUsd', 0))
            total_margin_used = float(account_data.get('totalMarginUsed', 0))
            
            # Calculate metrics
            cross_leverage = (total_ntl_pos / account_value) if account_value > 0 else 0
            
            # Start building message (Markdown format)
            message = "🔥 *Hyperliquid Positions Update*\n\n"
            
            # Account Summary
            message += "📊 *Account Summary*\n"
            message += f"• Account Equity: ${account_value:,.2f}\n"
            message += f"• Total Raw USD: ${total_raw_usd:,.2f}\n"
            message += f"• Total Notional: ${total_ntl_pos:,.2f}\n"
            message += f"• Margin Used: ${total_margin_used:,.2f}\n"
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
            self.logger.error(f"❌ Error formatting positions: {e}")
            return f"❌ Error formatting position data: {str(e)}"
    
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
            
            self.logger.info("✅ Message sent to Telegram successfully")
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Failed to send Telegram message: {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Unexpected error sending message: {e}")
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
                self.logger.info("✅ Inline command menu sent successfully")
            else:
                self.logger.error("❌ Failed to send inline command menu")
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Error sending inline command menu: {e}")
            return False
    
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
            self.logger.error(f"❌ Error answering callback query: {e}")
            return False
    
    def process_callback_query(self, callback_query: Dict):
        """Process inline button callback"""
        try:
            callback_data = callback_query.get('data', '')
            callback_id = callback_query.get('id', '')
            user = callback_query.get('from', {})
            username = user.get('username', user.get('first_name', 'Unknown'))
            
            self.logger.info(f"🔘 Received callback from {username}: {callback_data}")
            
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
                self.logger.warning(f"❓ Unknown callback data: {callback_data}")
                
        except Exception as e:
            self.logger.error(f"❌ Error processing callback query: {e}")
    
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
                self.logger.error(f"❌ Telegram API error: {data}")
                return []
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Failed to get Telegram updates: {e}")
            return []
        except Exception as e:
            self.logger.error(f"❌ Unexpected error getting updates: {e}")
            return []
    
    def handle_prices_command(self):
        """Handle /prices command"""
        self.logger.info("💰 Processing /prices command...")
        
        # Get current mark prices
        mids = self.get_mark_prices()
        
        if not mids:
            error_msg = "❌ Unable to fetch price data from Hyperliquid API"
            self.send_message(error_msg)
            return
        
        # Format and send prices
        message = self.format_prices_markdown(mids, self.price_symbols)
        self.send_message(message)
    
    def handle_position_command(self):
        """Handle /position command"""
        self.logger.info("📊 Processing /position command...")
        
        if not self.wallet_address:
            error_msg = "❌ Wallet address not configured. Please set HL_WALLET_ADDRESS in your environment."
            self.send_message(error_msg)
            return
        
        # Fetch data
        positions = self.fetch_positions()
        account_data = self.fetch_account_metrics()
        
        if positions is None or account_data is None:
            error_msg = "❌ Unable to fetch position data from Hyperliquid API"
            self.send_message(error_msg)
            return
        
        # Format and send positions
        message = self.format_positions_markdown(positions, account_data)
        self.send_message(message)
    
    def handle_help_command(self):
        """Handle /help command"""
        help_text = """
🤖 *Hyperliquid Bot Commands*

• `/prices` - Get current token prices
• `/position` - Get current positions and account summary
• `/help` - Show this help message

📊 *Configured Price Symbols*:
{symbols}

🔄 *Note*: This bot provides on-demand data from your Hyperliquid account.
        """.format(
            symbols=', '.join(self.price_symbols)
        ).strip()
        
        self.send_message(help_text)
    
    def process_message(self, message: Dict):
        """Process incoming message"""
        try:
            # Extract message text
            text = message.get('text', '').strip().lower()
            
            # Extract user info for logging
            user = message.get('from', {})
            username = user.get('username', user.get('first_name', 'Unknown'))
            
            self.logger.info(f"📨 Received message from {username}: {text}")
            
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
                
        except Exception as e:
            self.logger.error(f"❌ Error processing message: {e}")
            error_msg = "❌ Error processing your request. Please try again."
            self.send_message(error_msg)
    
    def run_bot(self):
        """Main bot loop"""
        try:
            console.print("🤖 [bold green]Telegram Bot Started[/bold green]")
            console.print(f"📊 Monitoring symbols: {', '.join(self.price_symbols)}")
            console.print("💡 Send /prices to get current token prices")
            console.print("📊 Send /position to get current positions and account summary")
            console.print("🛑 Press Ctrl+C to stop\n")
            
            while True:
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
                
        except KeyboardInterrupt:
            console.print("\n👋 [bold yellow]Bot stopped by user[/bold yellow]")
            self.logger.info("Bot stopped by user")
        except Exception as e:
            self.logger.error(f"❌ Fatal error in bot loop: {e}")
            console.print(f"❌ Fatal error: {e}", style="bold red")

def main():
    """Main entry point"""
    bot = HyperliquidTelegramBot()
    bot.run_bot()

if __name__ == "__main__":
    main()
