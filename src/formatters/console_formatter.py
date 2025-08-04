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
            self.console.print(Panel(
                "[red]❌ No active positions found.[/red]", 
                title="[bold cyan]📊 Position Summary[/bold cyan]",
                border_style="cyan"
            ))
            return
        
        # Account summary table with enhanced styling
        account_table = Table(
            show_header=False, 
            box=None, 
            padding=(0, 2),
            show_lines=False
        )
        account_table.add_column("Metric", style="bold bright_cyan", width=20)
        account_table.add_column("Value", style="bold bright_white", width=25)
        
        # Account value with color coding
        account_value_style = "bold bright_green" if account_summary.account_value > 0 else "bold bright_red"
        account_table.add_row(
            "💰 Account Value", 
            f"[{account_value_style}]${account_summary.account_value:,.2f}[/{account_value_style}]"
        )
        
        # Total P&L with dynamic coloring
        total_pnl = sum(p.unrealized_pnl for p in positions)
        pnl_color = "bright_green" if total_pnl >= 0 else "bright_red"
        pnl_symbol = "📈" if total_pnl >= 0 else "📉"
        account_table.add_row(
            f"{pnl_symbol} Total P&L", 
            f"[bold {pnl_color}]${total_pnl:+,.2f}[/bold {pnl_color}]"
        )
        
        # Leverage with warning colors
        leverage_color = "bright_red" if account_summary.cross_leverage > 20 else "bright_yellow" if account_summary.cross_leverage > 10 else "bright_green"
        account_table.add_row(
            "🔄 Cross Leverage", 
            f"[bold {leverage_color}]{account_summary.cross_leverage:.2f}x[/bold {leverage_color}]"
        )
        
        # Margin usage with risk coloring
        margin_ratio = account_summary.cross_margin_ratio
        margin_color = "bright_red" if margin_ratio > 90 else "bright_yellow" if margin_ratio > 70 else "bright_green"
        account_table.add_row(
            "💳 Margin Used", 
            f"[bold {margin_color}]${account_summary.total_margin_used:,.2f} ({margin_ratio:.1f}%)[/bold {margin_color}]"
        )
        
        # Available balance with color coding
        available_color = "bright_red" if account_summary.available_balance < 0 else "bright_green"
        account_table.add_row(
            "💵 Available", 
            f"[bold {available_color}]${account_summary.available_balance:,.2f}[/bold {available_color}]"
        )
        
        # Portfolio metrics if provided
        if portfolio_metrics:
            account_table.add_row("", "")  # Spacer
            account_table.add_row(
                "[dim]📊 Total Positions[/dim]", 
                f"[bold bright_white]{portfolio_metrics['total_positions']}[/bold bright_white]"
            )
            account_table.add_row(
                "[dim]✅ Profitable[/dim]", 
                f"[bold bright_green]{portfolio_metrics['profitable_positions']}[/bold bright_green]"
            )
            account_table.add_row(
                "[dim]❌ Losing[/dim]", 
                f"[bold bright_red]{portfolio_metrics['losing_positions']}[/bold bright_red]"
            )
            account_table.add_row(
                "[dim]📏 Avg Leverage[/dim]", 
                f"[bold bright_cyan]{portfolio_metrics['average_leverage']:.2f}x[/bold bright_cyan]"
            )
            account_table.add_row(
                "[dim]🎯 Largest Position[/dim]", 
                f"[bold bright_magenta]${portfolio_metrics['largest_position_value']:,.2f}[/bold bright_magenta]"
            )
        
        # Enhanced positions table with colorful styling
        positions_table = Table(
            title="[bold bright_cyan]🎯 Active Positions[/bold bright_cyan]",
            border_style="bright_cyan",
            header_style="bold bright_white on blue",
            show_lines=True,
            expand=True
        )
        
        positions_table.add_column("#", style="dim white", width=4, justify="center")
        positions_table.add_column("Symbol", style="bold bright_yellow", width=8, justify="center")
        positions_table.add_column("Side", style="bold", width=6, justify="center")
        positions_table.add_column("Size", justify="right", width=12)
        positions_table.add_column("Entry", justify="right", width=12)
        positions_table.add_column("Mark", justify="right", width=12)
        positions_table.add_column("Liq", justify="right", width=12)
        positions_table.add_column("P&L", justify="right", width=12)
        positions_table.add_column("P&L %", justify="right", width=8)
        positions_table.add_column("Leverage", justify="right", width=8)
        positions_table.add_column("Margin", justify="right", width=12)
        
        # Sort positions by unrealized PnL (most profitable first)
        sorted_positions = sorted(positions, key=lambda p: p.unrealized_pnl, reverse=True)
        
        for i, position in enumerate(sorted_positions, 1):
            # Dynamic styling based on position characteristics
            side_color = "bright_green" if position.side.value == "LONG" else "bright_red"
            side_icon = "📈" if position.side.value == "LONG" else "📉"
            
            pnl_color = "bright_green" if position.is_profitable else "bright_red"
            pnl_bg = "on green" if position.is_profitable else "on red"
            
            # Risk level coloring for leverage
            lev_color = "bright_red" if position.leverage > 25 else "bright_yellow" if position.leverage > 15 else "bright_green"
            
            # Liquidation distance coloring
            liq_distance = abs(position.mark_price - position.liq_price) / position.mark_price * 100
            liq_color = "bright_red" if liq_distance < 5 else "bright_yellow" if liq_distance < 15 else "bright_green"
            
            positions_table.add_row(
                f"[dim]{i}[/dim]",
                f"[bold bright_yellow]{position.symbol}[/bold bright_yellow]",
                f"[bold {side_color}]{side_icon} {position.side.value[:4]}[/bold {side_color}]",
                f"[bright_white]{position.size:,.4f}[/bright_white]",
                f"[bright_cyan]${position.entry_price:,.4f}[/bright_cyan]",
                f"[bright_magenta]${position.mark_price:,.4f}[/bright_magenta]",
                f"[{liq_color}]${position.liq_price:,.4f}[/{liq_color}]",
                f"[bold {pnl_color}]${position.unrealized_pnl:+,.2f}[/bold {pnl_color}]",
                f"[bold {pnl_color}]{position.pnl_percentage:+.2f}%[/bold {pnl_color}]",
                f"[bold {lev_color}]{position.leverage:.1f}x[/bold {lev_color}]",
                f"[bright_white]${position.margin_used:,.2f}[/bright_white]"
            )
        
        # Display everything with enhanced panels
        self.console.print(Panel(
            account_table, 
            title="[bold bright_cyan]📊 Account Summary[/bold bright_cyan]",
            border_style="bright_cyan",
            padding=(1, 2)
        ))
        self.console.print(positions_table)
    
    def format_prices_table(self, price_collection: PriceCollection, symbols: List[str]) -> None:
        """Format and print price data to console."""
        
        if len(price_collection) == 0:
            self.console.print(Panel(
                "[red]❌ No price data available.[/red]", 
                title="[bold bright_cyan]📈 Token Prices[/bold bright_cyan]",
                border_style="bright_cyan"
            ))
            return
        
        # Enhanced price table with colorful styling
        price_table = Table(
            title="[bold bright_cyan]📈 Token Prices[/bold bright_cyan]",
            border_style="bright_cyan",
            header_style="bold bright_white on blue",
            show_lines=True,
            expand=True
        )
        price_table.add_column("💰 Symbol", style="bold bright_yellow", width=12, justify="center")
        price_table.add_column("💵 Price", justify="right", style="bold bright_green", width=15)
        price_table.add_column("⏰ Age", justify="right", style="dim bright_white", width=10)
        
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
        
        # Add found prices with enhanced styling
        for symbol, price_data in found_symbols:
            age_seconds = price_data.age_seconds
            age_color = "bright_red" if age_seconds > 60 else "bright_yellow" if age_seconds > 30 else "bright_green"
            age_text = f"[{age_color}]{age_seconds:.0f}s[/{age_color}]"
            
            # Price formatting with dynamic colors based on value
            price_value = price_data.price
            if price_value > 1000:
                price_color = "bright_magenta"
            elif price_value > 100:
                price_color = "bright_cyan"
            elif price_value > 10:
                price_color = "bright_green"
            else:
                price_color = "bright_yellow"
            
            price_table.add_row(
                f"[bold bright_yellow]{symbol}[/bold bright_yellow]",
                f"[bold {price_color}]${price_value:,.4f}[/bold {price_color}]",
                age_text
            )
        
        self.console.print(price_table)
        
        # Show missing symbols if any
        if missing_symbols:
            self.console.print(Panel(
                f"[red]❌ Not found: {', '.join(missing_symbols)}[/red]",
                border_style="red"
            ))
        
        # Add timestamp with styling
        timestamp_panel = Panel(
            f"[dim bright_white]🕐 Updated: {datetime.now().strftime('%H:%M:%S')}[/dim bright_white]",
            border_style="dim"
        )
        self.console.print(timestamp_panel)
    
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
