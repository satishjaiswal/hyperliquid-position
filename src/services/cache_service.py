"""
Cache service for data caching and management.
"""

import time
import threading
from typing import Any, Optional, Dict, TypeVar, Generic
from dataclasses import dataclass
import logging

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """Represents a cached entry with timestamp."""
    data: T
    timestamp: float
    
    @property
    def age(self) -> float:
        """Get age of cache entry in seconds."""
        return time.time() - self.timestamp
    
    def is_expired(self, max_age: float) -> bool:
        """Check if cache entry is expired."""
        return self.age > max_age


class CacheService:
    """Thread-safe cache service for storing temporary data."""
    
    def __init__(self, default_ttl: int = 30):
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
    
    def get(self, key: str, max_age: Optional[float] = None) -> Optional[Any]:
        """Get cached data if not expired."""
        if max_age is None:
            max_age = self.default_ttl
        
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self.logger.debug(f"Cache miss for key: {key}")
                return None
            
            if entry.is_expired(max_age):
                self.logger.debug(f"Cache expired for key: {key} (age: {entry.age:.1f}s)")
                del self._cache[key]
                return None
            
            self.logger.debug(f"Cache hit for key: {key} (age: {entry.age:.1f}s)")
            return entry.data
    
    def set(self, key: str, data: Any) -> None:
        """Store data in cache with current timestamp."""
        with self._lock:
            self._cache[key] = CacheEntry(data=data, timestamp=time.time())
            self.logger.debug(f"Cached data for key: {key}")
    
    def delete(self, key: str) -> bool:
        """Delete cached data."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self.logger.debug(f"Deleted cache entry for key: {key}")
                return True
            return False
    
    def exists(self, key: str, max_age: Optional[float] = None) -> bool:
        """Check if key exists and is not expired."""
        return self.get(key, max_age) is not None
    
    def clear(self) -> int:
        """Clear all cached data and return count of cleared entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self.logger.info(f"Cleared {count} cache entries")
            return count
    
    def cleanup_expired(self, max_age: Optional[float] = None) -> int:
        """Remove expired entries and return count of removed entries."""
        if max_age is None:
            max_age = self.default_ttl
        
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired(max_age)
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                self.logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            entries = list(self._cache.values())
            
            if not entries:
                return {
                    'total_entries': 0,
                    'oldest_age': 0,
                    'newest_age': 0,
                    'average_age': 0
                }
            
            ages = [entry.age for entry in entries]
            
            return {
                'total_entries': len(entries),
                'oldest_age': max(ages),
                'newest_age': min(ages),
                'average_age': sum(ages) / len(ages)
            }
    
    def get_keys(self) -> list:
        """Get all cache keys."""
        with self._lock:
            return list(self._cache.keys())
    
    def __len__(self) -> int:
        """Get number of cached entries."""
        with self._lock:
            return len(self._cache)
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists in cache (regardless of expiration)."""
        with self._lock:
            return key in self._cache


class PositionCacheService(CacheService):
    """Specialized cache service for position data."""
    
    POSITIONS_KEY = "positions"
    ACCOUNT_KEY = "account_summary"
    PRICES_KEY = "mark_prices"
    FILLS_KEY = "user_fills"
    ORDERS_KEY = "open_orders"
    
    def __init__(self, default_ttl: int = 30):
        super().__init__(default_ttl)
        self.logger = logging.getLogger(__name__)
    
    def cache_positions(self, positions: list) -> None:
        """Cache position data."""
        self.set(self.POSITIONS_KEY, positions)
        self.logger.debug(f"Cached {len(positions)} positions")
    
    def get_positions(self, max_age: Optional[float] = None) -> Optional[list]:
        """Get cached positions."""
        return self.get(self.POSITIONS_KEY, max_age)
    
    def cache_account_summary(self, account_summary: Any) -> None:
        """Cache account summary data."""
        self.set(self.ACCOUNT_KEY, account_summary)
        self.logger.debug("Cached account summary")
    
    def get_account_summary(self, max_age: Optional[float] = None) -> Optional[Any]:
        """Get cached account summary."""
        return self.get(self.ACCOUNT_KEY, max_age)
    
    def cache_prices(self, prices: Any) -> None:
        """Cache price data."""
        self.set(self.PRICES_KEY, prices)
        self.logger.debug("Cached price data")
    
    def get_prices(self, max_age: Optional[float] = None) -> Optional[Any]:
        """Get cached prices."""
        return self.get(self.PRICES_KEY, max_age)
    
    def cache_fills(self, fills: list) -> None:
        """Cache user fills data."""
        self.set(self.FILLS_KEY, fills)
        self.logger.debug(f"Cached {len(fills)} fills")
    
    def get_fills(self, max_age: Optional[float] = None) -> Optional[list]:
        """Get cached fills."""
        return self.get(self.FILLS_KEY, max_age)
    
    def cache_orders(self, orders: list) -> None:
        """Cache open orders data."""
        self.set(self.ORDERS_KEY, orders)
        self.logger.debug(f"Cached {len(orders)} orders")
    
    def get_orders(self, max_age: Optional[float] = None) -> Optional[list]:
        """Get cached orders."""
        return self.get(self.ORDERS_KEY, max_age)
    
    def invalidate_all_position_data(self) -> None:
        """Invalidate all position-related cached data."""
        keys_to_delete = [
            self.POSITIONS_KEY,
            self.ACCOUNT_KEY,
            self.PRICES_KEY
        ]
        
        deleted_count = 0
        for key in keys_to_delete:
            if self.delete(key):
                deleted_count += 1
        
        self.logger.info(f"Invalidated {deleted_count} position data cache entries")
    
    def has_fresh_position_data(self, max_age: Optional[float] = None) -> bool:
        """Check if we have fresh position and account data."""
        return (
            self.exists(self.POSITIONS_KEY, max_age) and
            self.exists(self.ACCOUNT_KEY, max_age)
        )
