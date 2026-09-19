import time
import threading
from collections import OrderedDict
from typing import Any, Optional


class LRUCache:
    """
    A lightweight, thread-safe in-memory LRU cache with optional TTL.
    """

    def __init__(self, maxsize: int = 64, ttl_seconds: Optional[int] = None):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None

            value, timestamp = self._cache[key]

            # Check expiration
            if self.ttl_seconds is not None:
                if time.time() - timestamp > self.ttl_seconds:
                    del self._cache[key]
                    return None

            # Mark as recently used
            self._cache.move_to_end(key)
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (value, time.time())

            if len(self._cache) > self.maxsize:
                self._cache.popitem(last=False)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._cache)


# ============================================================
# Global Application Caches
# ============================================================

# Cache for loaded manifest.json files (prevents disk read + json parse per query)
manifest_cache = LRUCache(maxsize=32, ttl_seconds=3600)

# Cache for query vector embeddings (avoids redundant embedding calls for repeat queries)
query_embedding_cache = LRUCache(maxsize=128, ttl_seconds=1800)

# Cache for vector search results
search_result_cache = LRUCache(maxsize=64, ttl_seconds=900)

