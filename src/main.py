"""
Main application entry point for Hyperliquid position monitoring.
"""

import asyncio
import logging
import signal
import sys
import time
from typing import Optional

from .config.settings import Settings
from .config.environment import EnvironmentConfig
from .config.logging_config import setup_logging
from .services.hyperliquid_api import HyperliquidAPIService
from .services.telegram_service import TelegramService
from .services.cache_service import PositionCacheService
from .services.position_service import PositionService
from .formatters.telegram_formatter import TelegramFormatter
from .formatters.console_formatter import ConsoleFormatter
from .bot.telegram_bot import TelegramBot
from .monitor.position_monitor import PositionMonitor


class HyperliquidApp:
    """Main application class for Hyperliquid position monitoring."""
    
    def __init__(self):
        self.settings: Optional[Settings] = None
        self.api_service: Optional[HyperliquidAPIService] = None
        self.telegram_service: Optional[TelegramService] = None
        self.cache_service: Optional[PositionCacheService] = None
        self.position_service: Optional[PositionService] = None
        self.telegram_bot: Optional[TelegramBot] = None
        self.position_monitor: Optional[PositionMonitor] = None
        self.console_formatter = ConsoleFormatter()
        self.logger: Optional[logging.Logger] = None
        self.start_time = time.time()
        self.shutdown_event = asyncio.Event()
    
    def initialize(self) -> bool:
        """Initialize the application components."""
        try:
            # Validate environment
            env_config = EnvironmentConfig()
            if not env_config.validate_all():
                return False
            
            # Load settings from environment
            self.settings = Settings.from_env()
            
            # Setup logging
            setup_logging(self.settings.log_level, self.settings.log_directory)
            self.logger = logging.getLogger(__name__)
            
            self.logger.info("🚀 Starting Hyperliquid Position Monitor")
            
            # Initialize services
            self.api_service = HyperliquidAPIService(self.settings)
            self.telegram_service = TelegramService(self.settings)
            self.cache_service = PositionCacheService(self.settings.cache_duration)
            self.position_service = PositionService(self.api_service, self.cache_service)
            
            # Test connectivity
            if not self._test_connectivity():
                return False
            
            # Initialize bot components
            self.telegram_bot = TelegramBot(
                telegram_service=self.telegram_service,
                position_service=self.position_service,
                settings=self.settings
            )
            
            self.position_monitor = PositionMonitor(
                position_service=self.position_service,
                telegram_service=self.telegram_service,
                console_formatter=self.console_formatter,
                settings=self.settings
            )
            
            self.logger.info("✅ Application initialized successfully")
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Failed to initialize application: {e}")
            else:
                print(f"❌ Failed to initialize application: {e}")
            return False
    
    def _test_connectivity(self) -> bool:
        """Test connectivity to external services."""
        self.logger.info("🔍 Testing connectivity to external services...")
        
        # Test Hyperliquid API
        if not self.api_service.test_connectivity():
            self.logger.error("❌ Failed to connect to Hyperliquid API")
            return False
        
        # Test Telegram API
        if not self.telegram_service.test_connectivity():
            self.logger.error("❌ Failed to connect to Telegram API")
            return False
        
        self.logger.info("✅ All connectivity tests passed")
        return True
    
    async def run(self) -> None:
        """Run the main application loop."""
        if not self.initialize():
            sys.exit(1)
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        # Send startup message
        await self._send_startup_message()
        
        # Start background tasks
        tasks = []
        
        # Start Telegram bot
        if self.telegram_bot:
            bot_task = asyncio.create_task(self.telegram_bot.start())
            tasks.append(bot_task)
            self.logger.info("🤖 Telegram bot started")
        
        # Start position monitor
        if self.position_monitor:
            monitor_task = asyncio.create_task(self.position_monitor.start())
            tasks.append(monitor_task)
            self.logger.info("📊 Position monitor started")
        
        try:
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
        except KeyboardInterrupt:
            self.logger.info("🛑 Received keyboard interrupt")
        
        finally:
            await self._shutdown(tasks)
    
    async def _send_startup_message(self) -> None:
        """Send startup message to Telegram."""
        try:
            startup_message = TelegramFormatter.format_startup_message(
                self.settings.wallet_address,
                self.settings.refresh_interval
            )
            
            success = self.telegram_service.send_message(startup_message)
            if success:
                # Also send command menu
                self.telegram_service.send_command_menu()
                self.logger.info("📱 Startup message sent to Telegram")
            else:
                self.logger.warning("⚠️ Failed to send startup message to Telegram")
                
        except Exception as e:
            self.logger.error(f"❌ Error sending startup message: {e}")
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"🛑 Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self._trigger_shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def _trigger_shutdown(self) -> None:
        """Trigger application shutdown."""
        self.shutdown_event.set()
    
    async def _shutdown(self, tasks: list) -> None:
        """Gracefully shutdown the application."""
        self.logger.info("🛑 Shutting down application...")
        
        # Cancel all tasks
        for task in tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Close services
        if self.api_service:
            self.api_service.close()
        
        if self.telegram_service:
            self.telegram_service.close()
        
        # Clear cache
        if self.cache_service:
            cleared_count = self.cache_service.clear()
            self.logger.info(f"🧹 Cleared {cleared_count} cache entries")
        
        uptime = time.time() - self.start_time
        self.logger.info(f"✅ Application shutdown complete (uptime: {uptime:.1f}s)")
    
    def get_uptime(self) -> float:
        """Get application uptime in seconds."""
        return time.time() - self.start_time


async def main():
    """Main entry point."""
    app = HyperliquidApp()
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
