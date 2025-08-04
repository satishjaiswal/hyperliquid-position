"""
Position service for business logic and data orchestration.
"""

import logging
from typing import List, Optional, Tuple

from ..models.position import Position
from ..models.account import AccountSummary
from ..models.order import Order, OrderFill
from ..models.price import PriceCollection
from .hyperliquid_api import HyperliquidAPIService
from .cache_service import PositionCacheService


class PositionService:
    """Service for position-related business logic."""
    
    def __init__(self, api_service: HyperliquidAPIService, cache_service: PositionCacheService):
        self.api_service = api_service
        self.cache_service = cache_service
        self.logger = logging.getLogger(__name__)
    
    def get_positions_and_account(
        self, 
        use_cache: bool = True, 
        force_refresh: bool = False
    ) -> Tuple[Optional[List[Position]], Optional[AccountSummary]]:
        """Get positions and account summary with caching support."""
        
        # Check cache first if enabled and not forcing refresh
        if use_cache and not force_refresh:
            cached_positions = self.cache_service.get_positions()
            cached_account = self.cache_service.get_account_summary()
            
            if cached_positions is not None and cached_account is not None:
                self.logger.debug("Using cached position and account data")
                return cached_positions, cached_account
        
        # Fetch fresh data from API
        self.logger.info("Fetching fresh position and account data from API")
        
        positions = self.api_service.get_positions()
        account_summary = self.api_service.get_account_summary()
        
        if positions is None or account_summary is None:
            self.logger.error("Failed to fetch position or account data")
            return None, None
        
        # Cache the results if caching is enabled
        if use_cache:
            self.cache_service.cache_positions(positions)
            self.cache_service.cache_account_summary(account_summary)
            self.logger.debug("Cached fresh position and account data")
        
        return positions, account_summary
    
    def get_prices(
        self, 
        symbols: Optional[List[str]] = None, 
        use_cache: bool = True, 
        force_refresh: bool = False
    ) -> PriceCollection:
        """Get price data with caching support."""
        
        # Check cache first if enabled and not forcing refresh
        if use_cache and not force_refresh:
            cached_prices = self.cache_service.get_prices()
            if cached_prices is not None:
                self.logger.debug("Using cached price data")
                
                # If specific symbols requested, filter the cached data
                if symbols:
                    filtered_prices = PriceCollection()
                    for symbol in symbols:
                        price_data = cached_prices.get_price(symbol)
                        if price_data:
                            filtered_prices.add_price(symbol, price_data.price)
                    return filtered_prices
                
                return cached_prices
        
        # Fetch fresh data from API
        self.logger.info("Fetching fresh price data from API")
        
        price_collection = self.api_service.get_mark_prices()
        
        # Cache the results if caching is enabled
        if use_cache:
            self.cache_service.cache_prices(price_collection)
            self.logger.debug("Cached fresh price data")
        
        # Filter by symbols if requested
        if symbols:
            filtered_prices = PriceCollection()
            for symbol in symbols:
                price_data = price_collection.get_price(symbol)
                if price_data:
                    filtered_prices.add_price(symbol, price_data.price)
            return filtered_prices
        
        return price_collection
    
    def get_user_fills(
        self, 
        limit: int = 10, 
        use_cache: bool = False, 
        force_refresh: bool = False
    ) -> List[OrderFill]:
        """Get user fills with optional caching."""
        
        # Check cache first if enabled and not forcing refresh
        if use_cache and not force_refresh:
            cached_fills = self.cache_service.get_fills()
            if cached_fills is not None:
                self.logger.debug("Using cached fills data")
                return cached_fills[:limit]
        
        # Fetch fresh data from API
        self.logger.info("Fetching fresh fills data from API")
        
        fills = self.api_service.get_user_fills(limit)
        
        # Cache the results if caching is enabled
        if use_cache:
            self.cache_service.cache_fills(fills)
            self.logger.debug("Cached fresh fills data")
        
        return fills
    
    def get_open_orders(
        self, 
        limit: int = 10, 
        use_cache: bool = False, 
        force_refresh: bool = False
    ) -> List[Order]:
        """Get open orders with optional caching."""
        
        # Check cache first if enabled and not forcing refresh
        if use_cache and not force_refresh:
            cached_orders = self.cache_service.get_orders()
            if cached_orders is not None:
                self.logger.debug("Using cached orders data")
                return cached_orders[:limit]
        
        # Fetch fresh data from API
        self.logger.info("Fetching fresh orders data from API")
        
        orders = self.api_service.get_open_orders(limit)
        
        # Cache the results if caching is enabled
        if use_cache:
            self.cache_service.cache_orders(orders)
            self.logger.debug("Cached fresh orders data")
        
        return orders
    
    def invalidate_cache(self) -> None:
        """Invalidate all cached data."""
        self.cache_service.invalidate_all_position_data()
        self.logger.info("Invalidated all cached position data")
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return self.cache_service.get_stats()
    
    def calculate_portfolio_metrics(
        self, 
        positions: List[Position], 
        account_summary: AccountSummary
    ) -> dict:
        """Calculate additional portfolio metrics."""
        
        if not positions:
            return {
                'total_positions': 0,
                'profitable_positions': 0,
                'losing_positions': 0,
                'total_unrealized_pnl': 0.0,
                'largest_position_value': 0.0,
                'average_leverage': 0.0,
                'risk_metrics': {
                    'max_drawdown_risk': 0.0,
                    'concentration_risk': 0.0
                }
            }
        
        profitable_positions = [p for p in positions if p.is_profitable]
        losing_positions = [p for p in positions if not p.is_profitable]
        
        total_unrealized_pnl = sum(p.unrealized_pnl for p in positions)
        position_values = [p.position_value for p in positions]
        largest_position_value = max(position_values) if position_values else 0.0
        
        # Calculate weighted average leverage
        total_margin = sum(p.margin_used for p in positions)
        if total_margin > 0:
            weighted_leverage = sum(p.leverage * p.margin_used for p in positions) / total_margin
        else:
            weighted_leverage = 0.0
        
        # Risk metrics
        max_drawdown_risk = 0.0
        concentration_risk = 0.0
        
        if account_summary.account_value > 0:
            # Max drawdown risk: largest single position loss potential
            max_single_loss = min(p.unrealized_pnl for p in positions) if positions else 0.0
            max_drawdown_risk = abs(max_single_loss) / account_summary.account_value * 100
            
            # Concentration risk: largest position as % of account
            concentration_risk = largest_position_value / account_summary.account_value * 100
        
        return {
            'total_positions': len(positions),
            'profitable_positions': len(profitable_positions),
            'losing_positions': len(losing_positions),
            'total_unrealized_pnl': total_unrealized_pnl,
            'largest_position_value': largest_position_value,
            'average_leverage': weighted_leverage,
            'risk_metrics': {
                'max_drawdown_risk': max_drawdown_risk,
                'concentration_risk': concentration_risk
            }
        }
    
    def get_position_by_symbol(self, positions: List[Position], symbol: str) -> Optional[Position]:
        """Get position by symbol."""
        for position in positions:
            if position.symbol == symbol:
                return position
        return None
    
    def filter_positions_by_side(self, positions: List[Position], side: str) -> List[Position]:
        """Filter positions by side (LONG/SHORT)."""
        return [p for p in positions if p.side.value == side.upper()]
    
    def sort_positions_by_pnl(self, positions: List[Position], descending: bool = True) -> List[Position]:
        """Sort positions by unrealized PnL."""
        return sorted(positions, key=lambda p: p.unrealized_pnl, reverse=descending)
    
    def sort_positions_by_size(self, positions: List[Position], descending: bool = True) -> List[Position]:
        """Sort positions by position value."""
        return sorted(positions, key=lambda p: p.position_value, reverse=descending)
