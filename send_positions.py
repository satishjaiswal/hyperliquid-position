#!/usr/bin/env python3
"""
Hyperliquid Position Monitor
A CLI tool to fetch Hyperliquid perpetual positions and account data,
then send formatted updates to Telegram.
"""

import os
import sys
import time
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Any

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

class HyperliquidMonitor:
    def __init__(self):
        self.wallet_address = os.getenv('HL_WALLET_ADDRESS')
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.refresh_interval = int(os.getenv('REFRESH_INTERVAL_SECONDS', 300))
        
        self.api_base_url = "https://api.hyperliquid.xyz/info"
        
        # Setup logging
        self.setup_logging()
        
        # Validate configuration
        self.validate_config()
    
    def setup_logging(self):
        """Setup logging with both console and file output"""
        # Create logs directory
        os.makedirs('logs', exist_ok=True)
        
        # Create hourly log filename
        current_time = datetime.now()
        log_filename = f"logs/app_{current_time.strftime('%Y-%m-%d_%H')}.log"
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                RichHandler(console=console, rich_tracebacks=True),
                logging.FileHandler(log_filename, encoding='utf-8')
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("🚀 Hyperliquid Position Monitor started")
    
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
            self.logger.error(error_msg)
            console.print(f"❌ {error_msg}", style="bold red")
            sys.exit(1)
        
        self.logger.info("✅ Configuration validated successfully")
    
    def fetch_mark_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Fetch current mark prices for given symbols"""
        try:
            mark_prices = {}
            
            payload = {
                "type": "metaAndAssetCtxs"
            }
            
            response = requests.post(self.api_base_url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data and isinstance(data, list) and len(data) >= 2:
                meta_data = data[0]  # Meta data is in the first element
                asset_contexts = data[1]  # Asset contexts are in the second element
                
                # Extract universe (symbol list) from meta data
                universe = meta_data.get('universe', [])
                
                # Map symbols to their mark prices using index
                for symbol in symbols:
                    # Find the index of the symbol in the universe
                    symbol_index = None
                    for i, asset_info in enumerate(universe):
                        if asset_info.get('name') == symbol:
                            symbol_index = i
                            break
                    
                    if symbol_index is not None and symbol_index < len(asset_contexts):
                        ctx = asset_contexts[symbol_index]
                        mark_px = float(ctx.get('markPx', 0))
                        mark_prices[symbol] = mark_px
                    else:
                        self.logger.warning(f"Could not find mark price for {symbol}")
            
            self.logger.info(f"✅ Fetched mark prices for {len(mark_prices)} symbols")
            return mark_prices
            
        except Exception as e:
            self.logger.error(f"❌ Error fetching mark prices: {e}")
            return {}

    def fetch_positions(self) -> Optional[List[Dict[str, Any]]]:
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
                mark_prices = self.fetch_mark_prices(symbols_to_fetch)
                
                # Update positions with mark prices
                for pos in active_positions:
                    symbol = pos["symbol"]
                    if symbol in mark_prices:
                        pos["mark_price"] = mark_prices[symbol]
            
            self.logger.info(f"✅ Successfully fetched {len(active_positions)} active positions (filtered from {len(positions)} total)")
            
            return active_positions
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Failed to fetch positions: {e}")
            return None
        except Exception as e:
            self.logger.error(f"❌ Unexpected error fetching positions: {e}")
            return None
    
    def fetch_account_metrics(self) -> Optional[Dict[str, Any]]:
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
    
    def format_telegram_message(self, positions: List[Dict], account_data: Dict) -> str:
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
            
            # Start building message (HTML format)
            message = "🔥 <b>Hyperliquid Positions Update</b>\n\n"
            
            # Account Summary
            message += "📊 <b>Account Summary</b>\n"
            message += f"• Account Equity: ${account_value:,.2f}\n"
            message += f"• Total Raw USD: ${total_raw_usd:,.2f}\n"
            message += f"• Total Notional: ${total_ntl_pos:,.2f}\n"
            message += f"• Margin Used: ${total_margin_used:,.2f}\n"
            message += f"• Cross Margin Ratio: {cross_margin_ratio:.2f}%\n"
            message += f"• Cross Leverage: {cross_leverage:.2f}x\n\n"
            
            # Positions
            if positions:
                message += f"📈 <b>Open Positions ({len(positions)})</b>\n\n"
                
                for pos in positions:
                    symbol = pos.get('symbol', 'Unknown')
                    side = pos.get('side', 'Unknown')
                    size = pos.get('size', 0)
                    entry_px = pos.get('entry_price', 0)
                    mark_px = pos.get('mark_price', 0)
                    liq_px = pos.get('liq_price', 0)
                    unrealized_pnl = pos.get('unrealized_pnl', 0)
                    initial_margin = pos.get('margin_used', 0)
                    leverage = pos.get('leverage', 1)
                    
                    # Calculate PnL percentage
                    pnl_pct = (unrealized_pnl / (size * entry_px) * 100) if (size * entry_px) > 0 else 0
                    pnl_sign = "+" if unrealized_pnl >= 0 else ""
                    
                    # Color formatting for PnL (green for profit, red for loss)
                    if unrealized_pnl >= 0:
                        pnl_text = f'🟢 <b>{pnl_sign}${unrealized_pnl:,.2f} ({pnl_sign}{pnl_pct:.2f}%)</b>'
                    else:
                        pnl_text = f'🔴 <b>{pnl_sign}${unrealized_pnl:,.2f} ({pnl_sign}{pnl_pct:.2f}%)</b>'
                    
                    message += f"<b>{symbol}</b> ({side.upper()})\n"
                    message += f"• Size: {size:,.4f} {symbol}\n"
                    message += f"• Entry: ${entry_px:,.2f} | Mark: ${mark_px:,.2f}\n"
                    message += f"• Unrealized PnL: {pnl_text}\n"
                    message += f"• Liquidation: ${liq_px:,.2f}\n"
                    message += f"• Margin Required: ${initial_margin:,.2f}\n"
                    message += f"• Leverage: {leverage:.1f}x\n\n"
            else:
                message += "📈 <b>No Open Positions</b>\n\n"
            
            # Footer
            message += f"🕐 Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            
            return message
            
        except Exception as e:
            self.logger.error(f"❌ Error formatting message: {e}")
            return f"❌ Error formatting position data: {str(e)}"
    
    def send_to_telegram(self, message: str) -> bool:
        """Send message to Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            self.logger.info("📤 Sending message to Telegram...")
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            self.logger.info("✅ Message sent to Telegram successfully")
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Failed to send Telegram message: {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Unexpected error sending Telegram message: {e}")
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
            self.logger.error(f"❌ Error displaying console summary: {e}")
    
    def run_once(self) -> bool:
        """Run a single update cycle"""
        try:
            # Fetch data
            positions = self.fetch_positions()
            account_data = self.fetch_account_metrics()
            
            if positions is None or account_data is None:
                self.logger.error("❌ Failed to fetch required data")
                return False
            
            # Display console summary
            self.display_console_summary(positions, account_data)
            
            # Format and send message
            message = self.format_telegram_message(positions, account_data)
            success = self.send_to_telegram(message)
            
            if success:
                console.print("✅ Update completed successfully", style="bold green")
            else:
                console.print("❌ Failed to send Telegram message", style="bold red")
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Error in run_once: {e}")
            return False
    
    def main_loop(self, run_once: bool = False):
        """Main application loop"""
        try:
            console.print(Panel.fit(
                "🚀 Hyperliquid Position Monitor\n"
                f"Wallet: {self.wallet_address[:10]}...\n"
                f"Refresh: {self.refresh_interval}s",
                title="Starting Monitor",
                style="bold blue"
            ))
            
            iteration = 0
            
            while True:
                iteration += 1
                
                console.print(f"\n🔄 [bold cyan]Update #{iteration}[/bold cyan] - {datetime.now().strftime('%H:%M:%S')}")
                
                success = self.run_once()
                
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
            self.logger.info("Application stopped by user")
        except Exception as e:
            self.logger.error(f"❌ Fatal error in main loop: {e}")
            console.print(f"❌ Fatal error: {e}", style="bold red")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Hyperliquid Position Monitor")
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    args = parser.parse_args()
    
    monitor = HyperliquidMonitor()
    monitor.main_loop(run_once=args.once)

if __name__ == "__main__":
    main()
