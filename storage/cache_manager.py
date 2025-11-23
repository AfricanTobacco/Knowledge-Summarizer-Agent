"""
Cache manager for short-term storage using Cloud Storage (prototype) or Memorystore (production).
"""
import os
import json
from typing import Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import structlog

logger = structlog.get_logger()


class CloudStorageCache:
    """
    Simple file-based cache for prototype (uses Cloud Storage in GCP deployment).
    For production, this can be swapped with Memorystore Redis.
    """
    
    def __init__(
        self,
        cache_dir: str = "./cache",
        default_ttl_seconds: int = 604800  # 7 days
    ):
        """
        Initialize cache.
        
        Args:
            cache_dir: Directory for cache storage
            default_ttl_seconds: Default TTL in seconds (7 days default)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl_seconds = default_ttl_seconds
        
        logger.info("cache_initialized", cache_dir=str(self.cache_dir))
    
    def _get_cache_path(self, key: str) -> Path:
        """Get file path for cache key."""
        # Hash key to avoid filesystem issues
        import hashlib
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"
    
    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Set cache value.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl_seconds: TTL in seconds (uses default if not specified)
            
        Returns:
            True if successful
        """
        try:
            ttl = ttl_seconds or self.default_ttl_seconds
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)
            
            cache_data = {
                "key": key,
                "value": value,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": expires_at.isoformat()
            }
            
            cache_path = self._get_cache_path(key)
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f)
            
            logger.debug("cache_set", key=key, ttl_seconds=ttl)
            return True
            
        except Exception as e:
            logger.error("cache_set_failed", key=key, error=str(e))
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get cache value.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        try:
            cache_path = self._get_cache_path(key)
            
            if not cache_path.exists():
                logger.debug("cache_miss", key=key)
                return None
            
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
            
            # Check expiration
            expires_at = datetime.fromisoformat(cache_data["expires_at"])
            if datetime.utcnow() > expires_at:
                logger.debug("cache_expired", key=key)
                self.delete(key)
                return None
            
            logger.debug("cache_hit", key=key)
            return cache_data["value"]
            
        except Exception as e:
            logger.error("cache_get_failed", key=key, error=str(e))
            return None
    
    def delete(self, key: str) -> bool:
        """
        Delete cache entry.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful
        """
        try:
            cache_path = self._get_cache_path(key)
            if cache_path.exists():
                cache_path.unlink()
                logger.debug("cache_deleted", key=key)
            return True
        except Exception as e:
            logger.error("cache_delete_failed", key=key, error=str(e))
            return False
    
    def clear_expired(self) -> int:
        """
        Clear all expired cache entries.
        
        Returns:
            Number of entries cleared
        """
        cleared_count = 0
        
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r') as f:
                        cache_data = json.load(f)
                    
                    expires_at = datetime.fromisoformat(cache_data["expires_at"])
                    if datetime.utcnow() > expires_at:
                        cache_file.unlink()
                        cleared_count += 1
                        
                except Exception:
                    continue
            
            if cleared_count > 0:
                logger.info("expired_cache_cleared", count=cleared_count)
            
            return cleared_count
            
        except Exception as e:
            logger.error("cache_cleanup_failed", error=str(e))
            return 0
    
    def get_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            total_size_bytes = sum(f.stat().st_size for f in cache_files)
            
            valid_count = 0
            expired_count = 0
            
            for cache_file in cache_files:
                try:
                    with open(cache_file, 'r') as f:
                        cache_data = json.load(f)
                    
                    expires_at = datetime.fromisoformat(cache_data["expires_at"])
                    if datetime.utcnow() > expires_at:
                        expired_count += 1
                    else:
                        valid_count += 1
                except Exception:
                    continue
            
            return {
                "total_entries": len(cache_files),
                "valid_entries": valid_count,
                "expired_entries": expired_count,
                "total_size_bytes": total_size_bytes,
                "total_size_mb": round(total_size_bytes / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logger.error("cache_stats_failed", error=str(e))
            return {}


if __name__ == "__main__":
    # Test the cache
    cache = CloudStorageCache()
    
    # Test set/get
    print("Testing cache operations...")
    cache.set("test_key", {"message": "Hello, World!", "count": 42})
    
    value = cache.get("test_key")
    print(f"✅ Retrieved value: {value}")
    
    # Test expiration
    cache.set("short_ttl", "expires soon", ttl_seconds=1)
    import time
    time.sleep(2)
    expired_value = cache.get("short_ttl")
    print(f"✅ Expired value should be None: {expired_value}")
    
    # Test stats
    stats = cache.get_stats()
    print("\nCache Stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Cleanup
    cleared = cache.clear_expired()
    print(f"\n✅ Cleared {cleared} expired entries")
