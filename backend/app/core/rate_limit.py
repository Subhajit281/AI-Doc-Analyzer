"""Small process-local rate limiter for abuse-prone public endpoints.

For multi-instance deployments, replace this with a shared Redis-backed limiter.
The service currently runs as a single worker, so this protects the deployed
instance without adding another managed dependency.
"""

from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        now = monotonic()
        cutoff = now - window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, int(events[0] + window_seconds - now))
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests. Please try again shortly.",
                    headers={"Retry-After": str(retry_after)},
                )
            events.append(now)


rate_limiter = SlidingWindowRateLimiter()
