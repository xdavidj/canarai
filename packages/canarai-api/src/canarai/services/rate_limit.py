"""Reusable in-memory rate limiter."""

import time
from collections import defaultdict


class InMemoryRateLimiter:
    """Simple sliding-window rate limiter backed by an in-memory dict.

    Not suitable for multi-process deployments — use Redis for that.
    """

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        """Check if a request is allowed for the given key.

        Returns True if under the limit, False if rate limited.
        Automatically records the request if allowed.
        """
        now = time.monotonic()
        cutoff = now - self.window_seconds

        # Prune expired entries
        timestamps = self._requests[key]
        self._requests[key] = [t for t in timestamps if t > cutoff]

        if len(self._requests[key]) >= self.max_requests:
            return False

        self._requests[key].append(now)
        return True

    def reset(self, key: str) -> None:
        """Clear rate limit state for a key."""
        self._requests.pop(key, None)
