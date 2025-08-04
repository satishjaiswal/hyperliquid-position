"""
Telegram message formatter for position and trading data.
"""

from typing import List, Optional
from datetime import datetime

from ..models.position import Position
from ..models.account import AccountSummary
from ..models.order import Order, OrderFill
from ..models.price import PriceCollection


class TelegramFormatter:
    """Formats data for Telegram messages with Markdown support."""
    
    @staticmethod
    def format_positions_message(
        positions: List[Position], 
        account_summary: AccountSummary,
        portfolio_metrics: Optional[dict] = None
    ) -> str:
        """Format positions and account summary for Telegram."""
        
        if not positions:
            return "📊 *Position Summary*\n\n❌ No active positions found."
        
        # Header with account summary
        message = f"""📊 *Position Summary*

💰 *Account Value*: ${account_summary.account_value:,.2f}
📈 *Total P&L*: ${sum(p.unrealized_pnl for p in positions):+,.2f}
🔄 *Cross Leverage*: {account_summary.cross_leverage:.2f}x
💳 *Margin Used*: ${account_summary.total_margin_used:,.2f} ({account_summary.cross_margin_ratio:.1f}%)
💵 *Available*: ${account_summary.available_balance:,.2f}

"""
        
        # Add portfolio metrics if provided
        if portfolio_metrics:
            message += f"""📈 *Portfolio Metrics*:
• Positions: {portfolio_metrics['total_positions']} ({portfolio_metrics['profitable_positions']}✅ / {portfolio_metrics['losing_positions']}❌)
• Avg Leverage: {portfolio_metrics['average_leverage']:.2f}x
• Largest Position: ${portfolio_metrics['largest_position_value']:,.2f}

"""
        
        message += "🎯 *Active Positions*:\n\n"
        
        # Sort positions by unrealized PnL (most profitable first)
        sorted_positions = sorted(positions, key=lambda p: p.unrealized_pnl, reverse=True)
        
        for i, position in enumerate(sorted_positions, 1):
            pnl_emoji = "🟢" if position.is_profitable else "🔴"
            side_emoji = "📈" if position.side.value == "LONG" else "📉"
            
            message += f"""{i}. {side_emoji} *{position.symbol}* {position.side.value}
    📏 Size: {position.size:,.4f} @ ${position.entry_price:,.4f}
    📊 Mark: ${position.mark_price:,.4f}
    ⚠️ Liq: ${position.liq_price:,.4f}
    {pnl_emoji} P&L: ${position.unrealized_pnl:+,.2f} ({position.pnl_percentage:+.2f}%)
    ⚡ Leverage: {position.leverage:.1f}x
    💳 Margin: ${position.margin_used:,.2f}

"""
        
        return message.strip()
    
    @staticmethod
    def format_prices_message(price_collection: PriceCollection, symbols: List[str]) -> str:
        """Format price data for Telegram."""
        
        if len(price_collection) == 0:
            return "📈 *Token Prices*\n\n❌ No price data available."
        
        message = "📈 *Token Prices*\n\n"
        
        # Filter and format requested symbols
        found_symbols = []
        missing_symbols = []
        
        for symbol in symbols:
            price_data = price_collection.get_price(symbol)
            if price_data:
                found_symbols.append((symbol, price_data.price))
            else:
                missing_symbols.append(symbol)
        
        # Sort by symbol name
        found_symbols.sort(key=lambda x: x[0])
        
        # Add found prices
        for symbol, price in found_symbols:
            message += f"• *{symbol}*: ${price:,.4f}\n"
        
        # Add missing symbols note
        if missing_symbols:
            message += f"\n❌ *Not found*: {', '.join(missing_symbols)}"
        
        # Add timestamp
        message += f"\n\n🕐 *Updated*: {datetime.now().strftime('%H:%M:%S')}"
        
        return message
    
    @staticmethod
    def format_fills_message(fills: List[OrderFill]) -> str:
        """Format order fills for Telegram."""
        
        if not fills:
            return "📑 *Recent Fills*\n\n❌ No recent fills found."
        
        message = f"📑 *Recent Fills* (Last {len(fills)})\n\n"
        
        for i, fill in enumerate(fills, 1):
            pnl_emoji = "🟢" if fill.is_profitable else "🔴" if fill.closed_pnl < 0 else "⚪"
            role_emoji = "⚡" if fill.role.value == "TAKER" else "🎯"
            
            message += f"""{i}. {role_emoji} *{fill.symbol}* ({fill.role.value})
   Size: {fill.size:,.4f} @ ${fill.price:,.4f}
   {pnl_emoji} P&L: ${fill.closed_pnl:+,.2f} | Fee: ${fill.fee:,.4f}
   Time: {fill.formatted_timestamp}

"""
        
        return message.strip()
    
    @staticmethod
    def format_orders_message(orders: List[Order]) -> str:
        """Format open orders for Telegram."""
        
        if not orders:
            return "🧾 *Open Orders*\n\n❌ No open orders found."
        
        message = f"🧾 *Open Orders* ({len(orders)})\n\n"
        
        for i, order in enumerate(orders, 1):
            side_emoji = "🟢" if order.side.value == "BUY" else "🔴"
            type_emoji = "📌" if order.order_type.value == "LIMIT" else "⚡"
            
            message += f"""{i}. {side_emoji} {type_emoji} *{order.symbol}* {order.side.value}
   Size: {order.size:,.4f} @ ${order.price:,.4f}
   Type: {order.order_type.value}
   Value: ${order.order_value:,.2f}

"""
        
        return message.strip()
    
    @staticmethod
    def format_error_message(error_type: str, details: str = "") -> str:
        """Format error message for Telegram."""
        
        error_messages = {
            'api_error': '🚫 *API Error*\n\nFailed to fetch data from Hyperliquid API.',
            'network_error': '🌐 *Network Error*\n\nConnection issue detected.',
            'data_error': '📊 *Data Error*\n\nInvalid or missing data received.',
            'auth_error': '🔐 *Authentication Error*\n\nInvalid credentials or permissions.',
            'rate_limit': '⏱️ *Rate Limited*\n\nToo many requests. Please wait.',
            'unknown_error': '❓ *Unknown Error*\n\nAn unexpected error occurred.'
        }
        
        base_message = error_messages.get(error_type, error_messages['unknown_error'])
        
        if details:
            base_message += f"\n\n*Details*: {details}"
        
        base_message += "\n\n💡 Try again in a few moments or contact support if the issue persists."
        
        return base_message
    
    @staticmethod
    def format_startup_message(wallet_address: str, refresh_interval: int) -> str:
        """Format startup message for Telegram."""
        
        return f"""🚀 *Hyperliquid Bot Started*

✅ Successfully connected to Hyperliquid API
🔗 Monitoring wallet: `{wallet_address[:8]}...{wallet_address[-8:]}`
🔄 Refresh interval: {refresh_interval} seconds

📊 The bot will send periodic updates about your positions and account status.

Use /help to see available commands or interact with the menu below.
"""
    
    @staticmethod
    def format_status_message(
        api_connected: bool, 
        telegram_connected: bool, 
        cache_stats: dict,
        uptime_seconds: float
    ) -> str:
        """Format system status message for Telegram."""
        
        api_status = "✅ Connected" if api_connected else "❌ Disconnected"
        telegram_status = "✅ Connected" if telegram_connected else "❌ Disconnected"
        
        uptime_hours = uptime_seconds / 3600
        uptime_str = f"{uptime_hours:.1f} hours" if uptime_hours >= 1 else f"{uptime_seconds:.0f} seconds"
        
        return f"""🔧 *System Status*

🌐 *Hyperliquid API*: {api_status}
📱 *Telegram API*: {telegram_status}
⏱️ *Uptime*: {uptime_str}

💾 *Cache Statistics*:
• Entries: {cache_stats.get('total_entries', 0)}
• Avg Age: {cache_stats.get('average_age', 0):.1f}s
• Oldest: {cache_stats.get('oldest_age', 0):.1f}s

🔄 *Last Updated*: {datetime.now().strftime('%H:%M:%S')}
"""
    
    @staticmethod
    def escape_markdown(text: str) -> str:
        """Escape special Markdown characters."""
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        
        return text
    
    @staticmethod
    def format_command_response(command: str, success: bool, message: str = "") -> str:
        """Format command response message."""
        
        status_emoji = "✅" if success else "❌"
        status_text = "Success" if success else "Failed"
        
        response = f"{status_emoji} *Command {command}*: {status_text}"
        
        if message:
            response += f"\n\n{message}"
        
        return response
