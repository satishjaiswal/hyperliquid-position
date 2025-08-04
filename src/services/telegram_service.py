"""
Telegram service for message sending and bot interactions.
"""

import logging
from typing import Dict, List, Optional, Any
import requests

from ..config.settings import Settings


class TelegramService:
    """Service for Telegram bot interactions."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.timeout = settings.api_timeout
    
    def send_message(
        self, 
        message: str, 
        parse_mode: str = "Markdown", 
        reply_markup: Optional[dict] = None
    ) -> bool:
        """Send message to Telegram."""
        try:
            url = f"{self.settings.telegram_api_url}/sendMessage"
            
            payload = {
                'chat_id': self.settings.telegram_chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            if reply_markup:
                payload['reply_markup'] = reply_markup
            
            self.logger.debug(f"Sending Telegram message: {len(message)} characters")
            response = self.session.post(url, json=payload, timeout=self.settings.api_timeout)
            response.raise_for_status()
            
            self.logger.info("Message sent to Telegram successfully")
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to send Telegram message: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending message: {e}")
            return False
    
    def get_updates(self, offset: int = 0, timeout: int = 10, limit: int = 100) -> List[Dict]:
        """Get updates from Telegram."""
        try:
            url = f"{self.settings.telegram_api_url}/getUpdates"
            
            params = {
                'offset': offset,
                'timeout': timeout,
                'limit': limit
            }
            
            response = self.session.get(url, params=params, timeout=timeout + 5)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('ok'):
                updates = data.get('result', [])
                if updates:
                    self.logger.debug(f"Received {len(updates)} Telegram updates")
                return updates
            else:
                self.logger.error(f"Telegram API error: {data}")
                return []
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to get Telegram updates: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error getting updates: {e}")
            return []
    
    def answer_callback_query(self, callback_query_id: str, text: str = "") -> bool:
        """Answer callback query to remove loading state."""
        try:
            url = f"{self.settings.telegram_api_url}/answerCallbackQuery"
            
            payload = {
                'callback_query_id': callback_query_id,
                'text': text
            }
            
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            self.logger.debug("Callback query answered successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error answering callback query: {e}")
            return False
    
    def create_inline_keyboard(self, buttons: List[List[Dict[str, str]]]) -> Dict:
        """Create inline keyboard markup."""
        return {
            "inline_keyboard": buttons
        }
    
    def create_command_menu(self) -> Dict:
        """Create the main command menu inline keyboard."""
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
        return keyboard
    
    def send_command_menu(self) -> bool:
        """Send inline keyboard with command buttons."""
        try:
            keyboard = self.create_command_menu()
            
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
                self.logger.info("Inline command menu sent successfully")
            else:
                self.logger.error("Failed to send inline command menu")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending inline command menu: {e}")
            return False
    
    def send_help_message(self, price_symbols: List[str], refresh_interval: int) -> bool:
        """Send help message."""
        help_text = f"""
🤖 *Hyperliquid Bot Commands*

• `/prices` - Get current token prices
• `/position` - Get current positions and account summary
• `/fills` - View last 10 order fills
• `/openorders` - View current open orders
• `/help` - Show this help message

📊 *Configured Price Symbols*:
{', '.join(price_symbols)}

🔄 *Scheduled Updates*: Every {refresh_interval} seconds

💡 *Note*: This bot provides both scheduled updates and on-demand data from your Hyperliquid account.
        """.strip()
        
        success = self.send_message(help_text)
        if success:
            self.logger.info("Help message sent successfully")
        else:
            self.logger.error("Failed to send help message")
        
        return success
    
    def test_connectivity(self) -> bool:
        """Test Telegram API connectivity."""
        try:
            self.logger.info("Testing Telegram API connectivity...")
            response = self.session.get(
                "https://api.telegram.org",
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info("Telegram API connectivity test passed")
                return True
            else:
                self.logger.warning(f"Telegram API returned status: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Telegram API connectivity test failed: {e}")
            return False
    
    def close(self) -> None:
        """Close the session."""
        self.session.close()
        self.logger.debug("Telegram service session closed")
