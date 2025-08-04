"""
Application settings and configuration management.
"""

import os
from typing import List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Settings:
    """Application configuration settings."""
    
    # Hyperliquid Configuration
    wallet_address: str
    
    # Telegram Configuration
    telegram_bot_token: str
    telegram_chat_id: str
    
    # Application Configuration
    refresh_interval: int = 300
    price_symbols: List[str] = None
    
    # API Configuration
    api_base_url: str = "https://api.hyperliquid.xyz/info"
    api_timeout: int = 30
    
    # Cache Configuration
    cache_duration: int = 30
    
    # Logging Configuration
    log_level: str = "INFO"
    log_directory: str = "logs"
    
    def __post_init__(self):
        """Post-initialization processing."""
        if self.price_symbols is None:
            self.price_symbols = ['BTC', 'ETH', 'SOL']
    
    @classmethod
    def from_env(cls) -> 'Settings':
        """Create settings from environment variables."""
        load_dotenv()
        
        # Required environment variables
        wallet_address = os.getenv('HL_WALLET_ADDRESS')
        telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not wallet_address:
            raise ValueError("HL_WALLET_ADDRESS environment variable is required")
        if not telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        if not telegram_chat_id:
            raise ValueError("TELEGRAM_CHAT_ID environment variable is required")
        
        # Optional environment variables with defaults
        refresh_interval = int(os.getenv('REFRESH_INTERVAL_SECONDS', 300))
        price_symbols_str = os.getenv('PRICE_SYMBOLS', 'BTC,ETH,SOL')
        price_symbols = [s.strip() for s in price_symbols_str.split(',') if s.strip()]
        
        api_timeout = int(os.getenv('API_TIMEOUT', 30))
        cache_duration = int(os.getenv('CACHE_DURATION', 30))
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        log_directory = os.getenv('LOG_DIRECTORY', 'logs')
        
        return cls(
            wallet_address=wallet_address,
            telegram_bot_token=telegram_bot_token,
            telegram_chat_id=telegram_chat_id,
            refresh_interval=refresh_interval,
            price_symbols=price_symbols,
            api_timeout=api_timeout,
            cache_duration=cache_duration,
            log_level=log_level,
            log_directory=log_directory
        )
    
    def validate(self) -> None:
        """Validate configuration settings."""
        if not self.wallet_address:
            raise ValueError("Wallet address cannot be empty")
        if not self.telegram_bot_token:
            raise ValueError("Telegram bot token cannot be empty")
        if not self.telegram_chat_id:
            raise ValueError("Telegram chat ID cannot be empty")
        if self.refresh_interval < 1:
            raise ValueError("Refresh interval must be at least 1 second")
        if self.api_timeout < 1:
            raise ValueError("API timeout must be at least 1 second")
        if not self.price_symbols:
            raise ValueError("At least one price symbol must be configured")
    
    @property
    def telegram_api_url(self) -> str:
        """Get Telegram API URL."""
        return f"https://api.telegram.org/bot{self.telegram_bot_token}"
