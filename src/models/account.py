"""
Account data model.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AccountSummary:
    """Represents account summary information."""
    
    account_value: float
    total_ntl_pos: float
    total_raw_usd: float
    total_margin_used: float
    
    @classmethod
    def from_api_data(cls, data: dict) -> 'AccountSummary':
        """Create AccountSummary from Hyperliquid API data."""
        return cls(
            account_value=float(data.get('accountValue', 0)),
            total_ntl_pos=float(data.get('totalNtlPos', 0)),
            total_raw_usd=float(data.get('totalRawUsd', 0)),
            total_margin_used=float(data.get('totalMarginUsed', 0))
        )
    
    @property
    def cross_margin_ratio(self) -> float:
        """Calculate cross margin ratio as percentage."""
        if self.account_value > 0:
            return (self.total_margin_used / self.account_value) * 100
        return 0.0
    
    @property
    def cross_leverage(self) -> float:
        """Calculate cross leverage."""
        if self.account_value > 0:
            return self.total_ntl_pos / self.account_value
        return 0.0
    
    @property
    def available_balance(self) -> float:
        """Calculate available balance."""
        return self.account_value - self.total_margin_used
    
    @property
    def equity_utilization(self) -> float:
        """Calculate equity utilization percentage."""
        if self.account_value > 0:
            return (self.total_margin_used / self.account_value) * 100
        return 0.0
    
    def to_dict(self) -> dict:
        """Convert account summary to dictionary."""
        return {
            'account_value': self.account_value,
            'total_ntl_pos': self.total_ntl_pos,
            'total_raw_usd': self.total_raw_usd,
            'total_margin_used': self.total_margin_used,
            'cross_margin_ratio': self.cross_margin_ratio,
            'cross_leverage': self.cross_leverage,
            'available_balance': self.available_balance,
            'equity_utilization': self.equity_utilization
        }
