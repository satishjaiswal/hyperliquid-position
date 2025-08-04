"""
Console formatter for position and trading data with rich formatting.
"""

from typing import List, Optional
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns

from ..models.position import Position
from ..models.account import AccountSummary
from ..models.order import Order, OrderFill
from ..models.price import PriceCollection


class ConsoleFormatter:
    """Formats data for console output with rich formatting."""
    
    def __init__(self):
        self.console = Console()
    
    def format_positions_summary(
        self, 
        positions: List[Position], 
        account_summary: AccountSummary,
        portfolio_metrics: Optional[dict] = None
    ) -> None:
        """Format and print positions summary to console."""
        
        if not positions:
            self.console.print(Panel("❌ No active positions found.", title="📊 Position Summary"))
            return
        
        # Account summary table
        account_table = Table(show_header=False, box=None, padding=(0, 1))
        account_table.add_column("Metric", style="bold cyan")
        account_table.add_column("Value", style="bold white")
        
        account_table.add_row("💰 Account Value", f"${account_summary.account_value:,.2f}")
        
        total_pnl = sum(p.unrealized_pnl for p in positions)
        pnl_style = "bold green" if total_pnl >= 0 else "bold red"
        account_table.add_row("📈 Total P&L", f"${total_pnl:+,.2f}", style=pnl_style)
        
        account_table.add_row("🔄 Cross Leverage", f"{account_summary.cross_leverage:.2f}x")
        account_table.add_row("💳 Margin Used", f"${account_summary.total_margin_used:,.2f} ({account_summary.cross_margin_ratio:.1f}%)")
        account_table.add_row("💵 Available", f"${account_summary.available_balance:,.2f}")
        
        # Portfolio metrics if provided
        if portfolio_metrics:
            account_table.add_row("", "")  # Spacer
            account_table.add_row("📊 Total Positions", str(portfolio_metrics['total_positions']))
            account_table.add_row("✅ Profitable", str(portfolio_metrics['profitable_positions']))
            account_table.add_row("❌ Losing", str(portfolio_metrics['losing_positions']))
            account_table.add_row("📏 Avg Leverage", f"{portfolio_metrics['average_leverage']:.2f}x")
            account_table.add_row("🎯 Largest Position", f"${portfolio_metrics['largest_position_value']:,.2f}")
        
        # Positions table
        positions_table = Table(title="🎯 Active Positions")
        positions_table.add_column("#", style="dim", width=3)
        positions_table.add_column("Symbol", style="bold")
        positions_table.add_column("Side", style="bold")
        positions_table.add_column("Size", justify="right")
        positions_table.add_column("Entry", justify="right")
        positions_table.add_column("Mark", justify="right")
        positions_table.add_column("Liq", justify="right")
        positions_table.add_column("P&L", justify="right")
        positions_table.add_column("P&L %", justify="right")
        positions_table.add_column("Leverage", justify="right")
        positions_table.add_column("Margin", justify="right")
        
        # Sort positions by unrealized PnL (most profitable first)
        sorted_positions = sorted(positions, key=lambda p: p.unrealized_pnl, reverse=True)
        
        for i, position in enumerate(sorted_positions, 1):
            side_style = "green" if position.side.value == "LONG" else "red"
            pnl_style = "green" if position.is_profitable else "red"
            
            positions_table.add_row(
                str(i),
                position.symbol,
                position.side.value,
                f"{position.size:,.4f}",
                f"${position.entry_price:,.4f}",
                f"${position.mark_price:,.4f}",
                f"${position.liq_price:,.4f}",
                f"${position.unrealized_pnl:+,.2f}",
                f"{position.pnl_percentage:+.2f}%",
                f"{position.leverage:.1f}x",
                f"${position.margin_used:,.2f}",
                style=pnl_style if i > 3 else None  # Only color rows after first 3
            )
        
        # Display everything
        self.console.print(Panel(account_table, title="📊 Account Summary"))
        self.console.print(positions_table)
    
    def format_prices_table(self, price_collection: PriceCollection, symbols: List[str]) -> None:
        """Format and print price data to console."""
        
        if len(price_collection) == 0:
            self.console.print(Panel("❌ No price data available.", title="📈 Token Prices"))
            return
        
        # Create price table
        price_table = Table(title="📈 Token Prices")
        price_table.add_column("Symbol", style="bold cyan")
        price_table.add_column("Price", justify="right", style="bold white")
        price_table.add_column("Age", justify="right", style="dim")
        
        # Filter and sort requested symbols
        found_symbols = []
        missing_symbols = []
        
        for symbol in symbols:
            price_data = price_collection.get_price(symbol)
            if price_data:
                found_symbols.append((symbol, price_data))
            else:
                missing_symbols.append(symbol)
        
        # Sort by symbol name
        found_symbols.sort(key=lambda x: x[0])
        
        # Add found prices
        for symbol, price_data in found_symbols:
            age_text = f"{price_data.age_seconds:.0f}s"
            price_table.add_row(
                symbol,
                f"${price_data.price:,.4f}",
                age_text
            )
        
        self.console.print(price_table)
        
        # Show missing symbols if any
        if missing_symbols:
            missing_text = Text(f"❌ Not found: {', '.join(missing_symbols)}", style="red")
            self.console.print(missing_text)
        
        # Add timestamp
        timestamp = Text(f"🕐 Updated: {datetime.now().strftime('%H:%M:%S')}", style="dim")
        self.console.print(timestamp)
    
    def format_fills_table(self, fills: List[OrderFill]) -> None:
        """Format and print order fills to console."""
        
        if not fills:
            self.console.print(Panel("❌ No recent fills found.", title="📑 Recent Fills"))
            return
        
        fills_table = Table(title=f"📑 Recent Fills (Last {len(fills)})")
        fills_table.add_column("#", style="dim", width=3)
        fills_table.add_column("Symbol", style="bold")
        fills_table.add_column("Role", style="bold")
        fills_table.add_column("Size", justify="right")
        fills_table.add_column("Price", justify="right")
        fills_table.add_column("P&L", justify="right")
        fills_table.add_column("Fee", justify="right")
        fills_table.add_column("Time", style="dim")
        
        for i, fill in enumerate(fills, 1):
            pnl_style = "green" if fill.is_profitable else "red" if fill.closed_pnl < 0 else "white"
            role_style = "yellow" if fill.role.value == "TAKER" else "blue"
            
            fills_table.add_row(
                str(i),
                fill.symbol,
                fill.role.value,
                f"{fill.size:,.4f}",
                f"${fill.price:,.4f}",
                f"${fill.closed_pnl:+,.2f}",
                f"${fill.fee:,.4f}",
                fill.formatted_timestamp,
                style=pnl_style if abs(fill.closed_pnl) > 0 else None
            )
        
        self.console.print(fills_table)
    
    def format_orders_table(self, orders: List[Order]) -> None:
        """Format and print open orders to console."""
        
        if not orders:
            self.console.print(Panel("❌ No open orders found.", title="🧾 Open Orders"))
            return
        
        orders_table = Table(title=f"🧾 Open Orders ({len(orders)})")
        orders_table.add_column("#", style="dim", width=3)
        orders_table.add_column("Symbol", style="bold")
        orders_table.add_column("Side", style="bold")
        orders_table.add_column("Type", style="bold")
        orders_table.add_column("Size", justify="right")
        orders_table.add_column("Price", justify="right")
        orders_table.add_column("Value", justify="right")
        
        for i, order in enumerate(orders, 1):
            side_style = "green" if order.side.value == "BUY" else "red"
            type_style = "blue" if order.order_type.value == "LIMIT" else "yellow"
            
            orders_table.add_row(
                str(i),
                order.symbol,
                order.side.value,
                order.order_type.value,
                f"{order.size:,.4f}",
                f"${order.price:,.4f}",
                f"${order.order_value:,.2f}",
                style=side_style if i <= 3 else None  # Color first 3 rows
            )
        
        self.console.print(orders_table)
    
    def format_error_message(self, error_type: str, details: str = "") -> None:
        """Format and print error message to console."""
        
        error_messages = {
            'api_error': '🚫 API Error: Failed to fetch data from Hyperliquid API.',
            'network_error': '🌐 Network Error: Connection issue detected.',
            'data_error': '📊 Data Error: Invalid or missing data received.',
            'auth_error': '🔐 Authentication Error: Invalid credentials or permissions.',
            'rate_limit': '⏱️ Rate Limited: Too many requests. Please wait.',
            'unknown_error': '❓ Unknown Error: An unexpected error occurred.'
        }
        
        base_message = error_messages.get(error_type, error_messages['unknown_error'])
        
        if details:
            base_message += f"\n\nDetails: {details}"
        
        base_message += "\n\n💡 Try again in a few moments or contact support if the issue persists."
        
        self.console.print(Panel(base_message, title="❌ Error", style="red"))
    
    def format_startup_message(self, wallet_address: str, refresh_interval: int) -> None:
        """Format and print startup message to console."""
        
        startup_text = f"""🚀 Hyperliquid Bot Started

✅ Successfully connected to Hyperliquid API
🔗 Monitoring wallet: {wallet_address[:8]}...{wallet_address[-8:]}
🔄 Refresh interval: {refresh_interval} seconds

📊 The bot will monitor your positions and account status.
"""
        
        self.console.print(Panel(startup_text, title="🚀 Startup", style="green"))
    
    def format_status_message(
        self, 
        api_connected: bool, 
        telegram_connected: bool, 
        cache_stats: dict,
        uptime_seconds: float
    ) -> None:
        """Format and print system status to console."""
        
        status_table = Table(show_header=False, box=None, padding=(0, 1))
        status_table.add_column("Component", style="bold cyan")
        status_table.add_column("Status", style="bold")
        
        api_status = "✅ Connected" if api_connected else "❌ Disconnected"
        api_style = "green" if api_connected else "red"
        status_table.add_row("🌐 Hyperliquid API", api_status, style=api_style)
        
        telegram_status = "✅ Connected" if telegram_connected else "❌ Disconnected"
        telegram_style = "green" if telegram_connected else "red"
        status_table.add_row("📱 Telegram API", telegram_status, style=telegram_style)
        
        uptime_hours = uptime_seconds / 3600
        uptime_str = f"{uptime_hours:.1f} hours" if uptime_hours >= 1 else f"{uptime_seconds:.0f} seconds"
        status_table.add_row("⏱️ Uptime", uptime_str)
        
        status_table.add_row("", "")  # Spacer
        status_table.add_row("💾 Cache Entries", str(cache_stats.get('total_entries', 0)))
        status_table.add_row("📊 Avg Cache Age", f"{cache_stats.get('average_age', 0):.1f}s")
        status_table.add_row("⏰ Oldest Cache", f"{cache_stats.get('oldest_age', 0):.1f}s")
        
        status_table.add_row("", "")  # Spacer
        status_table.add_row("🔄 Last Updated", datetime.now().strftime('%H:%M:%S'))
        
        self.console.print(Panel(status_table, title="🔧 System Status"))
    
    def print_separator(self) -> None:
        """Print a separator line."""
        self.console.print("─" * 80, style="dim")
    
    def print_info(self, message: str) -> None:
        """Print info message."""
        self.console.print(f"ℹ️ {message}", style="blue")
    
    def print_success(self, message: str) -> None:
        """Print success message."""
        self.console.print(f"✅ {message}", style="green")
    
    def print_warning(self, message: str) -> None:
        """Print warning message."""
        self.console.print(f"⚠️ {message}", style="yellow")
    
    def print_error(self, message: str) -> None:
        """Print error message."""
        self.console.print(f"❌ {message}", style="red")
