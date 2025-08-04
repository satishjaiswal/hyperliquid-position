"""
Telegram bot for handling user commands and interactions.
"""

import asyncio
import logging
from typing import Dict, List, Optional

from ..config.settings import Settings
from ..services.telegram_service import TelegramService
from ..services.position_service import PositionService
from ..formatters.telegram_formatter import TelegramFormatter


class TelegramBot:
    """Telegram bot for handling user interactions."""
    
    def __init__(
        self, 
        telegram_service: TelegramService,
        position_service: PositionService,
        settings: Settings
    ):
        self.telegram_service = telegram_service
        self.position_service = position_service
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.last_update_id = 0
        self.running = False
        
        # Command handlers
        self.command_handlers = {
            '/start': self._handle_start,
            '/help': self._handle_help,
            '/position': self._handle_position,
            '/prices': self._handle_prices,
            '/fills': self._handle_fills,
            '/openorders': self._handle_openorders,
            '/status': self._handle_status,
            '/menu': self._handle_menu
        }
    
    async def start(self) -> None:
        """Start the Telegram bot."""
        self.running = True
        self.logger.info("🤖 Telegram bot started, listening for commands...")
        
        while self.running:
            try:
                await self._poll_updates()
                await asyncio.sleep(1)  # Small delay between polls
                
            except asyncio.CancelledError:
                self.logger.info("🛑 Telegram bot polling cancelled")
                break
            except Exception as e:
                self.logger.error(f"❌ Error in bot polling: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def stop(self) -> None:
        """Stop the Telegram bot."""
        self.running = False
        self.logger.info("🛑 Telegram bot stopped")
    
    async def _poll_updates(self) -> None:
        """Poll for new updates from Telegram."""
        updates = self.telegram_service.get_updates(
            offset=self.last_update_id + 1,
            timeout=10
        )
        
        for update in updates:
            self.last_update_id = update.get('update_id', 0)
            await self._process_update(update)
    
    async def _process_update(self, update: dict) -> None:
        """Process a single update from Telegram."""
        try:
            # Handle text messages
            if 'message' in update:
                message = update['message']
                await self._handle_message(message)
            
            # Handle callback queries (inline button presses)
            elif 'callback_query' in update:
                callback_query = update['callback_query']
                await self._handle_callback_query(callback_query)
                
        except Exception as e:
            self.logger.error(f"❌ Error processing update: {e}")
    
    async def _handle_message(self, message: dict) -> None:
        """Handle incoming text messages."""
        text = message.get('text', '').strip()
        chat_id = message.get('chat', {}).get('id')
        
        # Verify chat ID matches configured chat
        if str(chat_id) != str(self.settings.telegram_chat_id):
            self.logger.warning(f"⚠️ Unauthorized chat ID: {chat_id}")
            return
        
        self.logger.info(f"📨 Received message: {text}")
        
        # Handle commands
        if text.startswith('/'):
            command = text.split()[0].lower()
            if command in self.command_handlers:
                await self.command_handlers[command]()
            else:
                await self._handle_unknown_command(text)
        else:
            # Handle non-command messages
            await self._handle_text_message(text)
    
    async def _handle_callback_query(self, callback_query: dict) -> None:
        """Handle callback queries from inline keyboards."""
        callback_data = callback_query.get('data', '')
        callback_query_id = callback_query.get('id', '')
        
        self.logger.info(f"🔘 Received callback: {callback_data}")
        
        # Answer the callback query to remove loading state
        self.telegram_service.answer_callback_query(callback_query_id)
        
        # Handle the callback as a command
        if callback_data.startswith('/'):
            command = callback_data.lower()
            if command in self.command_handlers:
                await self.command_handlers[command]()
            else:
                await self._handle_unknown_command(callback_data)
    
    async def _handle_start(self) -> None:
        """Handle /start command."""
        await self._handle_menu()
    
    async def _handle_menu(self) -> None:
        """Handle /menu command - show inline keyboard."""
        success = self.telegram_service.send_command_menu()
        if not success:
            error_msg = TelegramFormatter.format_error_message(
                'network_error', 
                'Failed to send menu'
            )
            self.telegram_service.send_message(error_msg)
    
    async def _handle_help(self) -> None:
        """Handle /help command."""
        success = self.telegram_service.send_help_message(
            self.settings.price_symbols,
            self.settings.refresh_interval_seconds
        )
        
        if not success:
            error_msg = TelegramFormatter.format_error_message(
                'network_error', 
                'Failed to send help message'
            )
            self.telegram_service.send_message(error_msg)
    
    async def _handle_position(self) -> None:
        """Handle /position command."""
        try:
            self.logger.info("📊 Processing position command...")
            
            # Get positions and account data
            positions, account_summary = self.position_service.get_positions_and_account(
                use_cache=True, 
                force_refresh=False
            )
            
            if positions is None or account_summary is None:
                error_msg = TelegramFormatter.format_error_message(
                    'api_error',
                    'Failed to fetch position data'
                )
                self.telegram_service.send_message(error_msg)
                return
            
            # Calculate portfolio metrics
            portfolio_metrics = self.position_service.calculate_portfolio_metrics(
                positions, account_summary
            )
            
            # Format and send message
            message = TelegramFormatter.format_positions_message(
                positions, account_summary, portfolio_metrics
            )
            
            success = self.telegram_service.send_message(message)
            if not success:
                error_msg = TelegramFormatter.format_error_message(
                    'network_error',
                    'Failed to send position data'
                )
                self.telegram_service.send_message(error_msg)
            
        except Exception as e:
            self.logger.error(f"❌ Error handling position command: {e}")
            error_msg = TelegramFormatter.format_error_message(
                'unknown_error',
                str(e)
            )
            self.telegram_service.send_message(error_msg)
    
    async def _handle_prices(self) -> None:
        """Handle /prices command."""
        try:
            self.logger.info("📈 Processing prices command...")
            
            # Get price data
            price_collection = self.position_service.get_prices(
                symbols=self.settings.price_symbols,
                use_cache=True,
                force_refresh=False
            )
            
            # Format and send message
            message = TelegramFormatter.format_prices_message(
                price_collection, self.settings.price_symbols
            )
            
            success = self.telegram_service.send_message(message)
            if not success:
                error_msg = TelegramFormatter.format_error_message(
                    'network_error',
                    'Failed to send price data'
                )
                self.telegram_service.send_message(error_msg)
            
        except Exception as e:
            self.logger.error(f"❌ Error handling prices command: {e}")
            error_msg = TelegramFormatter.format_error_message(
                'unknown_error',
                str(e)
            )
            self.telegram_service.send_message(error_msg)
    
    async def _handle_fills(self) -> None:
        """Handle /fills command."""
        try:
            self.logger.info("📑 Processing fills command...")
            
            # Get fills data
            fills = self.position_service.get_user_fills(
                limit=10,
                use_cache=False,  # Always fetch fresh fills
                force_refresh=True
            )
            
            # Format and send message
            message = TelegramFormatter.format_fills_message(fills)
            
            success = self.telegram_service.send_message(message)
            if not success:
                error_msg = TelegramFormatter.format_error_message(
                    'network_error',
                    'Failed to send fills data'
                )
                self.telegram_service.send_message(error_msg)
            
        except Exception as e:
            self.logger.error(f"❌ Error handling fills command: {e}")
            error_msg = TelegramFormatter.format_error_message(
                'unknown_error',
                str(e)
            )
            self.telegram_service.send_message(error_msg)
    
    async def _handle_openorders(self) -> None:
        """Handle /openorders command."""
        try:
            self.logger.info("🧾 Processing open orders command...")
            
            # Get orders data
            orders = self.position_service.get_open_orders(
                limit=10,
                use_cache=False,  # Always fetch fresh orders
                force_refresh=True
            )
            
            # Format and send message
            message = TelegramFormatter.format_orders_message(orders)
            
            success = self.telegram_service.send_message(message)
            if not success:
                error_msg = TelegramFormatter.format_error_message(
                    'network_error',
                    'Failed to send orders data'
                )
                self.telegram_service.send_message(error_msg)
            
        except Exception as e:
            self.logger.error(f"❌ Error handling orders command: {e}")
            error_msg = TelegramFormatter.format_error_message(
                'unknown_error',
                str(e)
            )
            self.telegram_service.send_message(error_msg)
    
    async def _handle_status(self) -> None:
        """Handle /status command."""
        try:
            self.logger.info("🔧 Processing status command...")
            
            # Test connectivity
            api_connected = self.position_service.api_service.test_connectivity()
            telegram_connected = self.telegram_service.test_connectivity()
            
            # Get cache stats
            cache_stats = self.position_service.get_cache_stats()
            
            # Calculate uptime (this would need to be passed from main app)
            uptime_seconds = 0  # Placeholder
            
            # Format and send message
            message = TelegramFormatter.format_status_message(
                api_connected, telegram_connected, cache_stats, uptime_seconds
            )
            
            success = self.telegram_service.send_message(message)
            if not success:
                error_msg = TelegramFormatter.format_error_message(
                    'network_error',
                    'Failed to send status data'
                )
                self.telegram_service.send_message(error_msg)
            
        except Exception as e:
            self.logger.error(f"❌ Error handling status command: {e}")
            error_msg = TelegramFormatter.format_error_message(
                'unknown_error',
                str(e)
            )
            self.telegram_service.send_message(error_msg)
    
    async def _handle_unknown_command(self, command: str) -> None:
        """Handle unknown commands."""
        message = f"❓ Unknown command: `{command}`\n\nUse /help to see available commands or /menu for the interactive menu."
        self.telegram_service.send_message(message)
    
    async def _handle_text_message(self, text: str) -> None:
        """Handle non-command text messages."""
        # For now, just show the menu
        await self._handle_menu()
