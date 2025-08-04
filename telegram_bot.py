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
                
                # Safely extract size with null check
                szi_value = position_data.get("szi")
                if szi_value is None:
                    continue  # Skip if no size data
                
                size = abs(float(szi_value))
                
                # Skip zero-size positions (not open)
                if size == 0:
                    continue
                
                side = "LONG" if float(szi_value) > 0 else "SHORT"
                coin = position_data.get('coin', 'Unknown')
                symbols_to_fetch.append(coin)
                
                # Extract leverage value from nested structure with null checks
                leverage_data = position_data.get("leverage", {})
                if isinstance(leverage_data, dict):
                    leverage_value = leverage_data.get("value", 1)
                else:
                    leverage_value = leverage_data
                
                # Safely convert all numeric fields with null checks
                entry_px = position_data.get("entryPx", 0)
                liq_px = position_data.get("liquidationPx", 0)
                unrealized_pnl = position_data.get("unrealizedPnl", 0)
                margin_used = position_data.get("marginUsed", 0)
                
                active_positions.append({
                    "symbol": coin,
                    "side": side,
                    "size": size,
                    "entry_price": float(entry_px) if entry_px is not None else 0.0,
                    "mark_price": 0,  # Will be updated below
                    "liq_price": float(liq_px) if liq_px is not None else 0.0,
                    "unrealized_pnl": float(unrealized_pnl) if unrealized_pnl is not None else 0.0,
                    "leverage": float(leverage_value) if leverage_value is not None else 1.0,
                    "margin_used": float(margin_used) if margin_used is not None else 0.0
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
    
    def fetch_user_fills(self) -> Optional[List[Dict]]:
        """Fetch last 10 order fills from Hyperliquid API"""
        try:
            payload = {
                "type": "userFills",
                "user": self.wallet_address
            }
            
            self.logger.info("📑 Fetching user fills from Hyperliquid API...")
            response = requests.post(self.api_base_url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            fills = data if isinstance(data, list) else []
            
            # Sort by timestamp (most recent first) and limit to 10
            fills.sort(key=lambda x: x.get('time', 0), reverse=True)
            recent_fills = fills[:10]
            
            self.logger.info(f"✅ Successfully fetched {len(recent_fills)} recent fills")
            return recent_fills
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Failed to fetch user fills: {e}")
            return None
        except Exception as e:
            self.logger.error(f"❌ Unexpected error fetching user fills: {e}")
            return None
    
    def fetch_open_orders(self) -> Optional[List[Dict]]:
        """Fetch open orders from Hyperliquid API"""
        try:
            payload = {
                "type": "openOrders",
                "user": self.wallet_address
            }
            
            self.logger.info("🧾 Fetching open orders from Hyperliquid API...")
            response = requests.post(self.api_base_url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            orders = data if isinstance(data, list) else []
            
            # Limit to 10 most recent orders
            recent_orders = orders[:10]
            
            self.logger.info(f"✅ Successfully fetched {len(recent_orders)} open orders")
            return recent_orders
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Failed to fetch open orders: {e}")
            return None
        except Exception as e:
            self.logger.error(f"❌ Unexpected error fetching open orders: {e}")
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
    
    def format_fills_markdown(self, fills: List[Dict]) -> str:
        """Format order fills into a Telegram message"""
        try:
            if not fills:
                return "📑 *Recent Fills*\n\n❌ No recent fills found."
            
            message = "📑 *Recent Order Fills*\n\n"
            
            for fill in fills:
                # Extract fill data
                coin = fill.get('coin', 'Unknown')
                side_code = fill.get('side', 'Unknown')
                size = float(fill.get('sz', 0))
                price = float(fill.get('px', 0))
                timestamp = fill.get('time', 0)
                fee = float(fill.get('fee', 0))
                closed_pnl = float(fill.get('closedPnl', 0))
                
                # Convert timestamp to readable format (timestamp is in milliseconds)
                if timestamp:
                    from datetime import timezone
                    dt = datetime.fromtimestamp(timestamp / 1000, timezone.utc)
                    # Format as MM/DD/YYYY - HH:MM:SS to match user's preference
                    time_str = dt.strftime('%m/%d/%Y - %H:%M:%S')
                else:
                    time_str = 'Unknown'
                
                # Map side correctly for TAKER/MAKER roles
                if side_code == 'A':  # 'A' = TAKER (aggressor)
                    role = "TAKER"
                    side_emoji = "🔹"
                elif side_code == 'B':  # 'B' = MAKER (passive)
                    role = "MAKER"
                    side_emoji = "🔻"
                else:
                    role = side_code.upper()
                    side_emoji = "🔸"
                
                # Calculate trade value
                trade_value = size * price
                
                # Format PnL with appropriate emoji
                if closed_pnl > 0:
                    pnl_emoji = "🟢"
                    pnl_sign = "+"
                elif closed_pnl < 0:
                    pnl_emoji = "🔴"
                    pnl_sign = ""
                else:
                    pnl_emoji = "⚪"
                    pnl_sign = ""
                
                message += f"⏰ *{time_str}*\n"
                message += f"{side_emoji} *{coin}* | {role}\n"
                message += f"💰 Price: ${price:,.2f} | Size: {size:,.4f} {coin}\n"
                message += f"📊 Trade Value: ${trade_value:,.2f} USDC\n"
                message += f"💸 Fee: ${fee:,.4f} USDC\n"
                message += f"{pnl_emoji} Closed PnL: {pnl_sign}${closed_pnl:,.4f} USDC\n\n"
            
            # Use UTC time for consistency
            from datetime import timezone
            now_utc = datetime.now(timezone.utc)
            message += f"🕐 *Updated*: {now_utc.strftime('%H:%M:%S UTC')}"
            
            return message
            
        except Exception as e:
            self.logger.error(f"❌ Error formatting fills: {e}")
            return f"❌ Error formatting fills data: {str(e)}"
    
    def format_open_orders_markdown(self, orders: List[Dict]) -> str:
        """Format open orders into a Telegram message"""
        try:
            if not orders:
                return "🧾 *Open Orders*\n\n❌ No open orders found."
            
            message = "🧾 *Open Orders*\n\n"
            
            for order in orders:
                # Debug: Log the raw order data to understand the structure
                self.logger.info(f"🔍 Raw order data: {order}")
                
                # Extract order data - try multiple possible field names
                coin = order.get('coin', order.get('symbol', 'Unknown'))
                size = float(order.get('sz', order.get('size', 0)))
                limit_px = float(order.get('limitPx', order.get('px', order.get('price', 0))))
                order_type = order.get('orderType', order.get('type', 'LIMIT')).upper()
                
                # Get side field - according to Hyperliquid SDK: 'A' = sell, 'B' = buy
                side_code = order.get('side', '')
                
                # Determine side and emoji based on side field
                if side_code == 'A':  # 'A' = SELL
                    side = "SELL"
                    emoji = "🟥"
                elif side_code == 'B':  # 'B' = BUY
                    side = "BUY"
                    emoji = "🟩"
                else:
                    # Fallback if side field is missing or unknown
                    side = "UNKNOWN"
                    emoji = "🔸"
                    # Log this case for debugging
                    self.logger.warning(f"⚠️ Could not determine order side for {coin}. side={side_code}, raw order: {order}")
                
                # Determine order type display
                if order_type == 'LIMIT':
                    type_display = 'LIMIT'
                elif order_type == 'STOP':
                    type_display = 'STOP'
                else:
                    type_display = order_type
                
                message += f"{emoji} *{coin}* | {side} {size:,.4f} @ ${limit_px:,.2f} | {type_display}\n"
            
            message += f"\n🕐 *Updated*: {datetime.now().strftime('%H:%M:%S UTC')}"
            
            return message
            
        except Exception as e:
            self.logger.error(f"❌ Error formatting open orders: {e}")
            return f"❌ Error formatting open orders data: {str(e)}"
    
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
                        {"text": "📑 Fills", "callback_data": "/fills"},
                        {"text": "🧾 Open Orders", "callback_data": "/openorders"}
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
📑 *Fills* - View last 10 order fills
🧾 *Open Orders* - View current open orders
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
            elif callback_data == '/fills':
                self.handle_fills_command()
            elif callback_data == '/openorders':
                self.handle_open_orders_command()
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
    
    def handle_fills_command(self):
        """Handle /fills command"""
        self.logger.info("📑 Processing /fills command...")
        
        if not self.wallet_address:
            error_msg = "❌ Wallet address not configured. Please set HL_WALLET_ADDRESS in your environment."
            self.send_message(error_msg)
            return
        
        # Fetch fills data
        fills = self.fetch_user_fills()
        
        if fills is None:
            error_msg = "❌ Unable to fetch fills data from Hyperliquid API"
            self.send_message(error_msg)
            return
        
        # Format and send fills
        message = self.format_fills_markdown(fills)
        self.send_message(message)
    
    def handle_open_orders_command(self):
        """Handle /openorders command"""
        self.logger.info("🧾 Processing /openorders command...")
        
        if not self.wallet_address:
            error_msg = "❌ Wallet address not configured. Please set HL_WALLET_ADDRESS in your environment."
            self.send_message(error_msg)
            return
        
        # Fetch open orders data
        orders = self.fetch_open_orders()
        
        if orders is None:
            error_msg = "❌ Unable to fetch open orders data from Hyperliquid API"
            self.send_message(error_msg)
            return
        
        # Format and send open orders
        message = self.format_open_orders_markdown(orders)
        self.send_message(message)
    
    def handle_help_command(self):
        """Handle /help command"""
        help_text = """
🤖 *Hyperliquid Bot Commands*

• `/prices` - Get current token prices
• `/position` - Get current positions and account summary
• `/fills` - View last 10 order fills
• `/openorders` - View current open orders
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
            elif text == '/fills':
                self.handle_fills_command()
            elif text == '/openorders':
                self.handle_open_orders_command()
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
