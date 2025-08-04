"""
Position data model.
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class PositionSide(Enum):
    """Position side enumeration."""
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class Position:
    """Represents a trading position."""
    
    symbol: str
    side: PositionSide
    size: float
    entry_price: float
    mark_price: float
    liq_price: float
    unrealized_pnl: float
    leverage: float
    margin_used: float
    
    @classmethod
    def from_api_data(cls, data: dict) -> 'Position':
        """Create Position from Hyperliquid API data."""
        position_data = data.get("position", {})
        
        # Safely extract size with null check
        szi_value = position_data.get("szi")
        if szi_value is None:
            raise ValueError("Position size (szi) is None")
        
        size = abs(float(szi_value))
        side = PositionSide.LONG if float(szi_value) > 0 else PositionSide.SHORT
        
        # Extract leverage value from nested structure with null checks
        leverage_data = position_data.get("leverage", {})
        if isinstance(leverage_data, dict):
            leverage_value = leverage_data.get("value", 1)
        else:
            leverage_value = leverage_data
        
        # Safely convert all numeric fields with null checks
        entry_px = position_data.get("entryPx", 0)
        liq_px = position_data.get("liquidationPx", 0)
        unrealized_pnl = position_data.get("unrealizedPnl", 0)
        margin_used = position_data.get("marginUsed", 0)
        
        return cls(
            symbol=position_data.get('coin', 'Unknown'),
            side=side,
            size=size,
            entry_price=float(entry_px) if entry_px is not None else 0.0,
            mark_price=0.0,  # Will be updated separately
            liq_price=float(liq_px) if liq_px is not None else 0.0,
            unrealized_pnl=float(unrealized_pnl) if unrealized_pnl is not None else 0.0,
            leverage=float(leverage_value) if leverage_value is not None else 1.0,
            margin_used=float(margin_used) if margin_used is not None else 0.0
        )
    
    @property
    def pnl_percentage(self) -> float:
        """Calculate PnL percentage."""
        if self.size * self.entry_price > 0:
            return (self.unrealized_pnl / (self.size * self.entry_price)) * 100
        return 0.0
    
    @property
    def is_profitable(self) -> bool:
        """Check if position is profitable."""
        return self.unrealized_pnl >= 0
    
    @property
    def position_value(self) -> float:
        """Calculate current position value."""
        return self.size * self.mark_price
    
    def update_mark_price(self, mark_price: float) -> None:
        """Update the mark price for this position."""
        self.mark_price = mark_price
    
    def to_dict(self) -> dict:
        """Convert position to dictionary."""
        return {
            'symbol': self.symbol,
            'side': self.side.value,
            'size': self.size,
            'entry_price': self.entry_price,
            'mark_price': self.mark_price,
            'liq_price': self.liq_price,
            'unrealized_pnl': self.unrealized_pnl,
            'leverage': self.leverage,
            'margin_used': self.margin_used,
            'pnl_percentage': self.pnl_percentage,
            'is_profitable': self.is_profitable,
            'position_value': self.position_value
        }
