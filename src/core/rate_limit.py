"""Rate limiter (sliding window) and concurrency limiter per agent."""
from __future__ import annotations

import asyncio
import time
import threading
from collections import defaultdict


class RateLimiter:
    """Sliding-window rate limiter: max N requests per 60-second window per agent."""

    def __init__(self) -> None:
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def check(self, agent_id: str, limit: int) -> bool:
        """Return True if the request is within rate limit."""
        now = time.monotonic()
        cutoff = now - 60.0

        with self._lock:
            timestamps = self._windows[agent_id]
            # Prune old entries
            self._windows[agent_id] = [t for t in timestamps if t > cutoff]
            return len(self._windows[agent_id]) < limit

    def record(self, agent_id: str) -> None:
        """Record a request for rate limiting."""
        now = time.monotonic()
        with self._lock:
            self._windows[agent_id].append(now)


class ConcurrencyLimiter:
    """Per-agent concurrency limiter using asyncio.Semaphore."""

    def __init__(self) -> None:
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._lock = threading.Lock()

    def get_semaphore(self, agent_id: str, max_concurrency: int) -> asyncio.Semaphore:
        """Get or create a semaphore for the given agent."""
        with self._lock:
            if agent_id not in self._semaphores:
                self._semaphores[agent_id] = asyncio.Semaphore(max_concurrency)
            return self._semaphores[agent_id]
