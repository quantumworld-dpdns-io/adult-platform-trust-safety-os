"""Thread-safe, asyncio-compatible token-bucket rate limiter."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RateLimitStats:
    """Snapshot of rate-limiter state."""

    capacity: int
    tokens: float
    refill_rate: float  # tokens per second
    total_acquired: int
    total_rejected: int


class TokenBucketRateLimiter:
    """A classic token-bucket rate limiter with asyncio support.

    Each bucket has a fixed *capacity* and refills at *refill_rate* tokens
    per second.  Callers invoke :meth:`acquire` which returns ``True`` when a
    token is available, or ``False`` when the caller should back off.

    The limiter is safe to use from multiple asyncio tasks concurrently; it
    uses a lock to protect internal state.
    """

    def __init__(
        self,
        capacity: int,
        refill_rate: float,
        initial_tokens: Optional[float] = None,
    ) -> None:
        """Initialise the bucket.

        Args:
            capacity: Maximum number of tokens the bucket can hold.
            refill_rate: Tokens added per second.
            initial_tokens: Starting token count (defaults to *capacity*).
        """
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        if refill_rate <= 0:
            raise ValueError("refill_rate must be > 0")

        self._capacity = capacity
        self._refill_rate = refill_rate
        self._tokens = float(initial_tokens if initial_tokens is not None else capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()
        self._total_acquired = 0
        self._total_rejected = 0

    # ── Public API ─────────────────────────────────────────────

    async def acquire(self, tokens: int = 1) -> bool:
        """Attempt to consume *tokens* from the bucket.

        Returns:
            ``True`` if the tokens were granted, ``False`` otherwise.
        """
        async with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                self._total_acquired += 1
                return True
            self._total_rejected += 1
            return False

    async def peek(self) -> float:
        """Return the current number of available tokens (without consuming)."""
        async with self._lock:
            self._refill()
            return self._tokens

    async def reset(self, tokens: Optional[float] = None) -> None:
        """Reset the bucket to full (or a specific token count)."""
        async with self._lock:
            self._tokens = float(tokens if tokens is not None else self._capacity)
            self._last_refill = time.monotonic()

    async def get_stats(self) -> RateLimitStats:
        """Return a snapshot of the bucket's state."""
        async with self._lock:
            self._refill()
            return RateLimitStats(
                capacity=self._capacity,
                tokens=self._tokens,
                refill_rate=self._refill_rate,
                total_acquired=self._total_acquired,
                total_rejected=self._total_rejected,
            )

    # ── Internals ──────────────────────────────────────────────

    def _refill(self) -> None:
        """Add tokens based on elapsed wall-clock time (caller must hold lock)."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        if elapsed <= 0:
            return
        self._tokens = min(
            self._capacity,
            self._tokens + elapsed * self._refill_rate,
        )
        self._last_refill = now
