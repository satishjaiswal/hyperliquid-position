"""
Order and order fill data models.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from enum import Enum


class OrderSide(Enum):
    """Order side enumeration."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """Order type enumeration."""
    LIMIT = "LIMIT"
    STOP = "STOP"
    MARKET = "MARKET"


class FillRole(Enum):
    """Fill role enumeration."""
    TAKER = "TAKER"
    MAKER = "MAKER"


@dataclass
class Order:
    """Represents an open order."""
    
    symbol: str
    side: OrderSide
    size: float
    price: float
    order_type: OrderType
    
    @classmethod
    def from_api_data(cls, data: dict) -> 'Order':
        """Create Order from Hyperliquid API data."""
        # Extract order data - try multiple possible field names
        symbol = data.get('coin', data.get('symbol', 'Unknown'))
        size = float(data.get('sz', data.get('size', 0)))
        price = float(data.get('limitPx', data.get('px', data.get('price', 0))))
        order_type_str = data.get('orderType', data.get('type', 'LIMIT')).upper()
        
        # Map order type
        try:
            order_type = OrderType(order_type_str)
        except ValueError:
            order_type = OrderType.LIMIT
        
        # Get side field - according to Hyperliquid SDK: 'A' = sell, 'B' = buy
        side_code = data.get('side', '')
        
        # Determine side based on side field
        if side_code == 'A':  # 'A' = SELL
            side = OrderSide.SELL
        elif side_code == 'B':  # 'B' = BUY
            side = OrderSide.BUY
        else:
            # Fallback - this shouldn't happen with proper API data
            side = OrderSide.BUY
        
        return cls(
            symbol=symbol,
            side=side,
            size=size,
            price=price,
            order_type=order_type
        )
    
    @property
    def order_value(self) -> float:
        """Calculate order value."""
        return self.size * self.price
    
    def to_dict(self) -> dict:
        """Convert order to dictionary."""
        return {
            'symbol': self.symbol,
            'side': self.side.value,
            'size': self.size,
            'price': self.price,
            'order_type': self.order_type.value,
            'order_value': self.order_value
        }


@dataclass
class OrderFill:
    """Represents an executed order fill."""
    
    symbol: str
    role: FillRole
    size: float
    price: float
    timestamp: datetime
    fee: float
    closed_pnl: float
    
    @classmethod
    def from_api_data(cls, data: dict) -> 'OrderFill':
        """Create OrderFill from Hyperliquid API data."""
        # Extract fill data
        symbol = data.get('coin', 'Unknown')
        side_code = data.get('side', 'Unknown')
        size = float(data.get('sz', 0))
        price = float(data.get('px', 0))
        timestamp_ms = data.get('time', 0)
        fee = float(data.get('fee', 0))
        closed_pnl = float(data.get('closedPnl', 0))
        
        # Convert timestamp to datetime (timestamp is in milliseconds)
        if timestamp_ms:
            timestamp = datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)
        
        # Map side correctly for TAKER/MAKER roles
        if side_code == 'A':  # 'A' = TAKER (aggressor)
            role = FillRole.TAKER
        elif side_code == 'B':  # 'B' = MAKER (passive)
            role = FillRole.MAKER
        else:
            role = FillRole.TAKER  # Default fallback
        
        return cls(
            symbol=symbol,
            role=role,
            size=size,
            price=price,
            timestamp=timestamp,
            fee=fee,
            closed_pnl=closed_pnl
        )
    
    @property
    def trade_value(self) -> float:
        """Calculate trade value."""
        return self.size * self.price
    
    @property
    def is_profitable(self) -> bool:
        """Check if fill resulted in profit."""
        return self.closed_pnl > 0
    
    @property
    def formatted_timestamp(self) -> str:
        """Get formatted timestamp string."""
        return self.timestamp.strftime('%m/%d/%Y - %H:%M:%S')
    
    def to_dict(self) -> dict:
        """Convert order fill to dictionary."""
        return {
            'symbol': self.symbol,
            'role': self.role.value,
            'size': self.size,
            'price': self.price,
            'timestamp': self.timestamp.isoformat(),
            'formatted_timestamp': self.formatted_timestamp,
            'fee': self.fee,
            'closed_pnl': self.closed_pnl,
            'trade_value': self.trade_value,
            'is_profitable': self.is_profitable
        }
