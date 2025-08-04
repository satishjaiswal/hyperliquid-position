"""
Position monitor for automated data collection and reporting.
"""

import asyncio
import logging
from typing import Optional, List
from datetime import datetime

from ..config.settings import Settings
from ..services.position_service import PositionService
from ..services.telegram_service import TelegramService
from ..formatters.telegram_formatter import TelegramFormatter
from ..formatters.console_formatter import ConsoleFormatter
from ..models.position import Position
from ..models.account import AccountSummary


class PositionMonitor:
    """Monitors positions and sends periodic updates."""
    
    def __init__(
        self,
        position_service: PositionService,
        telegram_service: TelegramService,
        console_formatter: ConsoleFormatter,
        settings: Settings
    ):
        self.position_service = position_service
        self.telegram_service = telegram_service
        self.console_formatter = console_formatter
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.last_positions: Optional[List[Position]] = None
        self.last_account: Optional[AccountSummary] = None
        self.update_count = 0
    
    async def start(self) -> None:
        """Start the position monitor."""
        self.running = True
        self.logger.info("📊 Position monitor started")
        
        while self.running:
            try:
                await self._monitor_cycle()
                await asyncio.sleep(self.settings.refresh_interval)
                
            except asyncio.CancelledError:
                self.logger.info("🛑 Position monitor cancelled")
                break
            except Exception as e:
                self.logger.error(f"❌ Error in monitor cycle: {e}")
                await asyncio.sleep(30)  # Wait before retrying
    
    async def stop(self) -> None:
        """Stop the position monitor."""
        self.running = False
        self.logger.info("🛑 Position monitor stopped")
    
    async def _monitor_cycle(self) -> None:
        """Execute one monitoring cycle."""
        self.update_count += 1
        self.logger.info(f"🔄 Starting monitor cycle #{self.update_count}")
        
        try:
            # Fetch fresh data
            positions, account_summary = self.position_service.get_positions_and_account(
                use_cache=False,  # Always fetch fresh data for monitoring
                force_refresh=True
            )
            
            if positions is None or account_summary is None:
                self.logger.error("❌ Failed to fetch position data in monitor cycle")
                return
            
            # Display to console
            await self._display_console_update(positions, account_summary)
            
            # Check for significant changes and send Telegram updates
            await self._check_and_send_updates(positions, account_summary)
            
            # Update last known state
            self.last_positions = positions
            self.last_account = account_summary
            
            # Cleanup cache periodically
            if self.update_count % 10 == 0:  # Every 10 cycles
                self._cleanup_cache()
            
        except Exception as e:
            self.logger.error(f"❌ Error in monitor cycle: {e}")
    
    async def _display_console_update(
        self, 
        positions: List[Position], 
        account_summary: AccountSummary
    ) -> None:
        """Display update to console."""
        try:
            # Calculate portfolio metrics
            portfolio_metrics = self.position_service.calculate_portfolio_metrics(
                positions, account_summary
            )
            
            # Print separator and timestamp
            self.console_formatter.print_separator()
            self.console_formatter.print_info(
                f"Monitor Update #{self.update_count} - {datetime.now().strftime('%H:%M:%S')}"
            )
            
            # Display positions summary
            self.console_formatter.format_positions_summary(
                positions, account_summary, portfolio_metrics
            )
            
        except Exception as e:
            self.logger.error(f"❌ Error displaying console update: {e}")
    
    async def _check_and_send_updates(
        self, 
        positions: List[Position], 
        account_summary: AccountSummary
    ) -> None:
        """Check for significant changes and send Telegram updates."""
        try:
            # Send periodic updates (every 12 cycles = 1 hour with 5min intervals)
            if self.update_count % 12 == 0:
                await self._send_periodic_update(positions, account_summary)
                return
            
            # Check for significant changes
            if self.last_positions is None or self.last_account is None:
                # First run - don't send update
                return
            
            # Check for new positions
            new_positions = self._detect_new_positions(positions)
            if new_positions:
                await self._send_new_positions_alert(new_positions)
            
            # Check for closed positions
            closed_positions = self._detect_closed_positions(positions)
            if closed_positions:
                await self._send_closed_positions_alert(closed_positions)
            
            # Check for significant PnL changes
            significant_changes = self._detect_significant_pnl_changes(positions)
            if significant_changes:
                await self._send_pnl_change_alert(significant_changes, account_summary)
            
        except Exception as e:
            self.logger.error(f"❌ Error checking for updates: {e}")
    
    async def _send_periodic_update(
        self, 
        positions: List[Position], 
        account_summary: AccountSummary
    ) -> None:
        """Send periodic position update."""
        try:
            self.logger.info("📱 Sending periodic position update")
            
            # Calculate portfolio metrics
            portfolio_metrics = self.position_service.calculate_portfolio_metrics(
                positions, account_summary
            )
            
            # Format message with periodic update header
            message = f"🕐 *Periodic Update* - {datetime.now().strftime('%H:%M')}\n\n"
            message += TelegramFormatter.format_positions_message(
                positions, account_summary, portfolio_metrics
            )
            
            success = self.telegram_service.send_message(message)
            if success:
                self.logger.info("✅ Periodic update sent successfully")
            else:
                self.logger.warning("⚠️ Failed to send periodic update")
                
        except Exception as e:
            self.logger.error(f"❌ Error sending periodic update: {e}")
    
    def _detect_new_positions(self, current_positions: List[Position]) -> List[Position]:
        """Detect new positions that weren't in the last update."""
        if not self.last_positions:
            return []
        
        last_symbols = {pos.symbol for pos in self.last_positions}
        new_positions = [
            pos for pos in current_positions 
            if pos.symbol not in last_symbols
        ]
        
        return new_positions
    
    def _detect_closed_positions(self, current_positions: List[Position]) -> List[Position]:
        """Detect positions that were closed since last update."""
        if not self.last_positions:
            return []
        
        current_symbols = {pos.symbol for pos in current_positions}
        closed_positions = [
            pos for pos in self.last_positions 
            if pos.symbol not in current_symbols
        ]
        
        return closed_positions
    
    def _detect_significant_pnl_changes(self, current_positions: List[Position]) -> List[dict]:
        """Detect significant PnL changes (>5% change or >$100)."""
        if not self.last_positions:
            return []
        
        # Create lookup for last positions
        last_pos_lookup = {pos.symbol: pos for pos in self.last_positions}
        
        significant_changes = []
        
        for current_pos in current_positions:
            last_pos = last_pos_lookup.get(current_pos.symbol)
            if not last_pos:
                continue
            
            pnl_change = current_pos.unrealized_pnl - last_pos.unrealized_pnl
            pnl_change_pct = 0
            
            if last_pos.unrealized_pnl != 0:
                pnl_change_pct = (pnl_change / abs(last_pos.unrealized_pnl)) * 100
            
            # Check if change is significant
            if abs(pnl_change) > 100 or abs(pnl_change_pct) > 5:
                significant_changes.append({
                    'position': current_pos,
                    'pnl_change': pnl_change,
                    'pnl_change_pct': pnl_change_pct,
                    'previous_pnl': last_pos.unrealized_pnl
                })
        
        return significant_changes
    
    async def _send_new_positions_alert(self, new_positions: List[Position]) -> None:
        """Send alert for new positions."""
        try:
            self.logger.info(f"🆕 Sending new positions alert for {len(new_positions)} positions")
            
            message = f"🆕 *New Position{'s' if len(new_positions) > 1 else ''}*\n\n"
            
            for pos in new_positions:
                side_emoji = "📈" if pos.side.value == "LONG" else "📉"
                message += f"{side_emoji} *{pos.symbol}* {pos.side.value}\n"
                message += f"   Size: {pos.size:,.4f} @ ${pos.entry_price:,.4f}\n"
                message += f"   Leverage: {pos.leverage:.1f}x\n\n"
            
            success = self.telegram_service.send_message(message)
            if success:
                self.logger.info("✅ New positions alert sent")
            else:
                self.logger.warning("⚠️ Failed to send new positions alert")
                
        except Exception as e:
            self.logger.error(f"❌ Error sending new positions alert: {e}")
    
    async def _send_closed_positions_alert(self, closed_positions: List[Position]) -> None:
        """Send alert for closed positions."""
        try:
            self.logger.info(f"🔒 Sending closed positions alert for {len(closed_positions)} positions")
            
            message = f"🔒 *Position{'s' if len(closed_positions) > 1 else ''} Closed*\n\n"
            
            for pos in closed_positions:
                pnl_emoji = "🟢" if pos.is_profitable else "🔴"
                side_emoji = "📈" if pos.side.value == "LONG" else "📉"
                message += f"{side_emoji} *{pos.symbol}* {pos.side.value}\n"
                message += f"   {pnl_emoji} Final P&L: ${pos.unrealized_pnl:+,.2f}\n\n"
            
            success = self.telegram_service.send_message(message)
            if success:
                self.logger.info("✅ Closed positions alert sent")
            else:
                self.logger.warning("⚠️ Failed to send closed positions alert")
                
        except Exception as e:
            self.logger.error(f"❌ Error sending closed positions alert: {e}")
    
    async def _send_pnl_change_alert(
        self, 
        significant_changes: List[dict], 
        account_summary: AccountSummary
    ) -> None:
        """Send alert for significant PnL changes."""
        try:
            self.logger.info(f"📊 Sending PnL change alert for {len(significant_changes)} positions")
            
            message = f"📊 *Significant P&L Change{'s' if len(significant_changes) > 1 else ''}*\n\n"
            
            for change in significant_changes:
                pos = change['position']
                pnl_change = change['pnl_change']
                pnl_change_pct = change['pnl_change_pct']
                
                change_emoji = "🟢" if pnl_change > 0 else "🔴"
                side_emoji = "📈" if pos.side.value == "LONG" else "📉"
                
                message += f"{side_emoji} *{pos.symbol}* {pos.side.value}\n"
                message += f"   {change_emoji} Change: ${pnl_change:+,.2f}"
                
                if pnl_change_pct != 0:
                    message += f" ({pnl_change_pct:+.1f}%)"
                
                message += f"\n   Current P&L: ${pos.unrealized_pnl:+,.2f}\n\n"
            
            success = self.telegram_service.send_message(message)
            if success:
                self.logger.info("✅ PnL change alert sent")
            else:
                self.logger.warning("⚠️ Failed to send PnL change alert")
                
        except Exception as e:
            self.logger.error(f"❌ Error sending PnL change alert: {e}")
    
    def _cleanup_cache(self) -> None:
        """Cleanup expired cache entries."""
        try:
            cleaned_count = self.position_service.cache_service.cleanup_expired()
            if cleaned_count > 0:
                self.logger.info(f"🧹 Cleaned up {cleaned_count} expired cache entries")
                
        except Exception as e:
            self.logger.error(f"❌ Error cleaning up cache: {e}")
