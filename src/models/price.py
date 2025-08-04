"""
Price data model.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class PriceData:
    """Represents price data for a symbol."""
    
    symbol: str
    price: float
    timestamp: datetime
    
    @classmethod
    def from_api_data(cls, symbol: str, price: float) -> 'PriceData':
        """Create PriceData from API data."""
        return cls(
            symbol=symbol,
            price=price,
            timestamp=datetime.now(timezone.utc)
        )
    
    @property
    def formatted_price(self) -> str:
        """Get formatted price string."""
        return f"${self.price:,.2f}"
    
    @property
    def age_seconds(self) -> float:
        """Get age of price data in seconds."""
        return (datetime.now(timezone.utc) - self.timestamp).total_seconds()
    
    @property
    def is_stale(self, max_age_seconds: int = 60) -> bool:
        """Check if price data is stale."""
        return self.age_seconds > max_age_seconds
    
    def to_dict(self) -> dict:
        """Convert price data to dictionary."""
        return {
            'symbol': self.symbol,
            'price': self.price,
            'formatted_price': self.formatted_price,
            'timestamp': self.timestamp.isoformat(),
            'age_seconds': self.age_seconds,
            'is_stale': self.is_stale()
        }


class PriceCollection:
    """Collection of price data for multiple symbols."""
    
    def __init__(self):
        self._prices: Dict[str, PriceData] = {}
    
    def add_price(self, symbol: str, price: float) -> None:
        """Add or update price for a symbol."""
        self._prices[symbol] = PriceData.from_api_data(symbol, price)
    
    def get_price(self, symbol: str) -> Optional[PriceData]:
        """Get price data for a symbol."""
        return self._prices.get(symbol)
    
    def get_price_value(self, symbol: str) -> Optional[float]:
        """Get price value for a symbol."""
        price_data = self.get_price(symbol)
        return price_data.price if price_data else None
    
    def has_symbol(self, symbol: str) -> bool:
        """Check if symbol exists in collection."""
        return symbol in self._prices
    
    def get_symbols(self) -> List[str]:
        """Get all symbols in collection."""
        return list(self._prices.keys())
    
    def get_all_prices(self) -> Dict[str, PriceData]:
        """Get all price data."""
        return self._prices.copy()
    
    def filter_symbols(self, symbols: List[str]) -> Dict[str, PriceData]:
        """Filter prices by symbol list."""
        return {
            symbol: self._prices[symbol] 
            for symbol in symbols 
            if symbol in self._prices
        }
    
    def remove_stale_prices(self, max_age_seconds: int = 60) -> int:
        """Remove stale prices and return count removed."""
        stale_symbols = [
            symbol for symbol, price_data in self._prices.items()
            if price_data.is_stale(max_age_seconds)
        ]
        
        for symbol in stale_symbols:
            del self._prices[symbol]
        
        return len(stale_symbols)
    
    def clear(self) -> None:
        """Clear all price data."""
        self._prices.clear()
    
    def __len__(self) -> int:
        """Get number of symbols in collection."""
        return len(self._prices)
    
    def __contains__(self, symbol: str) -> bool:
        """Check if symbol is in collection."""
        return symbol in self._prices
    
    def to_dict(self) -> dict:
        """Convert price collection to dictionary."""
        return {
            'prices': {symbol: price.to_dict() for symbol, price in self._prices.items()},
            'symbol_count': len(self._prices),
            'symbols': self.get_symbols()
        }
