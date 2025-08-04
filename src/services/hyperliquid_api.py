"""
Hyperliquid API service for data retrieval.
"""

import logging
from typing import List, Dict, Optional, Any
import requests

from ..config.settings import Settings
from ..models.position import Position
from ..models.account import AccountSummary
from ..models.order import Order, OrderFill
from ..models.price import PriceCollection


class HyperliquidAPIService:
    """Service for interacting with Hyperliquid API."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.timeout = settings.api_timeout
    
    def _make_request(self, payload: dict) -> Optional[dict]:
        """Make a request to the Hyperliquid API."""
        try:
            self.logger.debug(f"Making API request: {payload}")
            response = self.session.post(
                self.settings.api_base_url,
                json=payload,
                timeout=self.settings.api_timeout
            )
            response.raise_for_status()
            
            data = response.json()
            self.logger.debug(f"API response received: {len(str(data))} characters")
            return data
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in API request: {e}")
            return None
    
    def get_mark_prices(self) -> PriceCollection:
        """Fetch all current mark prices."""
        payload = {"type": "allMids"}
        
        self.logger.info("Fetching mark prices from Hyperliquid API...")
        data = self._make_request(payload)
        
        price_collection = PriceCollection()
        
        if not data:
            self.logger.error("Failed to fetch mark prices")
            return price_collection
        
        # The allMids API returns a dictionary with symbol: price_string format
        if isinstance(data, dict):
            for symbol, price_str in data.items():
                try:
                    # Skip entries that start with '@' (these are index-based entries)
                    if not symbol.startswith('@'):
                        price = float(price_str)
                        price_collection.add_price(symbol, price)
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Failed to parse price for {symbol}: {e}")
                    continue
        
        self.logger.info(f"Fetched {len(price_collection)} token prices")
        return price_collection
    
    def get_positions(self) -> List[Position]:
        """Fetch perpetual positions."""
        payload = {
            "type": "clearinghouseState",
            "user": self.settings.wallet_address
        }
        
        self.logger.info("Fetching positions from Hyperliquid API...")
        data = self._make_request(payload)
        
        if not data:
            self.logger.error("Failed to fetch positions")
            return []
        
        positions_data = data.get('assetPositions', [])
        self.logger.info(f"Found {len(positions_data)} positions in API response")
        
        # Filter out zero-size positions and create Position objects
        active_positions = []
        symbols_to_fetch = []
        
        for pos_data in positions_data:
            try:
                # Check if position has size
                position_info = pos_data.get("position", {})
                szi_value = position_info.get("szi")
                
                if szi_value is None or abs(float(szi_value)) == 0:
                    continue  # Skip zero-size positions
                
                position = Position.from_api_data(pos_data)
                active_positions.append(position)
                symbols_to_fetch.append(position.symbol)
                
            except (ValueError, KeyError) as e:
                self.logger.warning(f"Failed to parse position data: {e}")
                continue
        
        # Fetch mark prices for all symbols and update positions
        if symbols_to_fetch:
            self.logger.info("Fetching current mark prices for positions...")
            price_collection = self.get_mark_prices()
            
            for position in active_positions:
                mark_price = price_collection.get_price_value(position.symbol)
                if mark_price:
                    position.update_mark_price(mark_price)
        
        self.logger.info(f"Successfully processed {len(active_positions)} active positions")
        return active_positions
    
    def get_account_summary(self) -> Optional[AccountSummary]:
        """Fetch account summary."""
        payload = {
            "type": "clearinghouseState",
            "user": self.settings.wallet_address
        }
        
        self.logger.info("Fetching account metrics from Hyperliquid API...")
        data = self._make_request(payload)
        
        if not data:
            self.logger.error("Failed to fetch account metrics")
            return None
        
        # Extract account data from the response
        account_data = data.get('marginSummary', {})
        
        if not account_data:
            self.logger.warning("No margin summary found in API response")
            return None
        
        try:
            account_summary = AccountSummary.from_api_data(account_data)
            self.logger.info("Successfully fetched account metrics")
            return account_summary
            
        except (ValueError, KeyError) as e:
            self.logger.error(f"Failed to parse account data: {e}")
            return None
    
    def get_user_fills(self, limit: int = 10) -> List[OrderFill]:
        """Fetch user order fills."""
        payload = {
            "type": "userFills",
            "user": self.settings.wallet_address
        }
        
        self.logger.info("Fetching user fills from Hyperliquid API...")
        data = self._make_request(payload)
        
        if not data:
            self.logger.error("Failed to fetch user fills")
            return []
        
        fills_data = data if isinstance(data, list) else []
        
        # Sort by timestamp (most recent first) and limit
        fills_data.sort(key=lambda x: x.get('time', 0), reverse=True)
        recent_fills_data = fills_data[:limit]
        
        fills = []
        for fill_data in recent_fills_data:
            try:
                fill = OrderFill.from_api_data(fill_data)
                fills.append(fill)
            except (ValueError, KeyError) as e:
                self.logger.warning(f"Failed to parse fill data: {e}")
                continue
        
        self.logger.info(f"Successfully fetched {len(fills)} recent fills")
        return fills
    
    def get_open_orders(self, limit: int = 10) -> List[Order]:
        """Fetch open orders."""
        payload = {
            "type": "openOrders",
            "user": self.settings.wallet_address
        }
        
        self.logger.info("Fetching open orders from Hyperliquid API...")
        data = self._make_request(payload)
        
        if not data:
            self.logger.error("Failed to fetch open orders")
            return []
        
        orders_data = data if isinstance(data, list) else []
        
        # Limit to most recent orders
        recent_orders_data = orders_data[:limit]
        
        orders = []
        for order_data in recent_orders_data:
            try:
                order = Order.from_api_data(order_data)
                orders.append(order)
            except (ValueError, KeyError) as e:
                self.logger.warning(f"Failed to parse order data: {e}")
                self.logger.debug(f"Raw order data: {order_data}")
                continue
        
        self.logger.info(f"Successfully fetched {len(orders)} open orders")
        return orders
    
    def test_connectivity(self) -> bool:
        """Test API connectivity."""
        try:
            self.logger.info("Testing Hyperliquid API connectivity...")
            
            # Use a simple API call that doesn't require authentication
            test_payload = {"type": "allMids"}
            response = self.session.post(
                self.settings.api_base_url,
                json=test_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                # Try to parse the response to ensure it's valid
                data = response.json()
                if isinstance(data, dict) and len(data) > 0:
                    self.logger.info("Hyperliquid API connectivity test passed")
                    return True
                else:
                    self.logger.warning("Hyperliquid API returned empty or invalid data")
                    return False
            else:
                self.logger.warning(f"Hyperliquid API returned status: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Hyperliquid API connectivity test failed: {e}")
            return False
    
    def close(self) -> None:
        """Close the session."""
        self.session.close()
        self.logger.debug("API service session closed")
