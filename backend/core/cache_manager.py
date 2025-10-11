"""Prompt caching manager for Claude API responses."""

import hashlib
import json
import time
from typing import Dict, Any, Optional, List
from loguru import logger
from config import settings

# Constants
CACHE_CLEANUP_PERCENTAGE = 0.1  # Remove 10% of oldest entries when cleaning up
CACHE_KEY_PREFIX_LENGTH = 8  # Length of cache key prefix for logging


class PromptCacheManager:
    """Manages prompt caching for Claude API responses."""
    
    def __init__(self):
        """Initialize the cache manager."""
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = settings.cache_ttl_seconds
        self.max_entries = settings.max_cache_entries
        
        logger.info(f"Prompt cache manager initialized with TTL: {self.cache_ttl}s, Max entries: {self.max_entries}")
    
    def _generate_cache_key(self, messages: List[Dict[str, Any]], model: str, max_tokens: int, temperature: float) -> str:
        """Generate a cache key for the given parameters."""
        # Create a hash of the relevant parameters
        cache_data = {
            "messages": messages,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # Convert to JSON string and hash using SHA-256 for better security
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_string.encode()).hexdigest()
    
    def get_cached_response(self, messages: List[Dict[str, Any]], model: str, max_tokens: int, temperature: float) -> Optional[Dict[str, Any]]:
        """Get a cached response if available and not expired."""
        cache_key = self._generate_cache_key(messages, model, max_tokens, temperature)
        
        if cache_key in self.cache:
            cached_item = self.cache[cache_key]
            
            # Check if cache entry is still valid
            if time.time() - cached_item["timestamp"] < self.cache_ttl:
                logger.info(f"Cache hit for key: {cache_key[:CACHE_KEY_PREFIX_LENGTH]}...")
                return cached_item["response"]
            else:
                # Remove expired entry
                del self.cache[cache_key]
                logger.info(f"Cache entry expired for key: {cache_key[:CACHE_KEY_PREFIX_LENGTH]}...")
        
        return None
    
    def cache_response(self, messages: List[Dict[str, Any]], model: str, max_tokens: int, temperature: float, response: Dict[str, Any]) -> None:
        """Cache a response for future use."""
        cache_key = self._generate_cache_key(messages, model, max_tokens, temperature)
        
        # Clean up old entries if we're at the limit
        if len(self.cache) >= self.max_entries:
            self._cleanup_old_entries()
        
        # Cache the response
        self.cache[cache_key] = {
            "response": response,
            "timestamp": time.time(),
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        logger.info(f"Cached response for key: {cache_key[:CACHE_KEY_PREFIX_LENGTH]}... (total entries: {len(self.cache)})")
    
    def _cleanup_old_entries(self) -> None:
        """Remove old cache entries to stay within limits."""
        current_time = time.time()
        
        # Remove expired entries first
        expired_keys = [
            key for key, item in self.cache.items()
            if current_time - item["timestamp"] >= self.cache_ttl
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        # If still over limit, remove oldest entries
        if len(self.cache) >= self.max_entries:
            sorted_items = sorted(
                self.cache.items(),
                key=lambda x: x[1]["timestamp"]
            )
            
            # Remove oldest entries based on cleanup percentage
            remove_count = max(1, int(len(sorted_items) * CACHE_CLEANUP_PERCENTAGE))
            for key, _ in sorted_items[:remove_count]:
                del self.cache[key]
        
        logger.info(f"Cache cleanup completed. Remaining entries: {len(self.cache)}")
    
    def clear_cache(self) -> None:
        """Clear all cached entries."""
        self.cache.clear()
        logger.info("Cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        valid_entries = sum(
            1 for item in self.cache.values()
            if current_time - item["timestamp"] < self.cache_ttl
        )
        
        return {
            "total_entries": len(self.cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self.cache) - valid_entries,
            "cache_ttl": self.cache_ttl,
            "max_entries": self.max_entries,
            "cache_hit_rate": getattr(self, '_cache_hits', 0) / max(1, getattr(self, '_cache_requests', 0)) * 100
        }
    
    def increment_cache_hit(self) -> None:
        """Increment cache hit counter."""
        self._cache_hits = getattr(self, '_cache_hits', 0) + 1
    
    def increment_cache_request(self) -> None:
        """Increment cache request counter."""
        self._cache_requests = getattr(self, '_cache_requests', 0) + 1


# Global cache manager instance
cache_manager = PromptCacheManager()

