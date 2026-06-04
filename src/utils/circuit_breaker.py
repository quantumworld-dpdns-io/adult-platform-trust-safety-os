"""Circuit-breaker pattern with CLOSED / OPEN / HALF_OPEN states."""

from __future__ import annotations

import asyncio
import time
from enum import Enum
from typing import Any, Callable, Optional


class State(Enum):
    """Circuit-breaker states."""

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """Thread-safe, asyncio-compatible circuit breaker.

    Behaviour:
        * **CLOSED** – requests pass through normally. Each failure increments
          a counter. When failures reach *failure_threshold* the breaker trips
          to OPEN.
        * **OPEN** – requests are rejected immediately with
          ``CircuitOpenError``. After *recovery_timeout* seconds the breaker
          moves to HALF_OPEN.
        * **HALF_OPEN** – exactly one request is allowed through as a probe.
          If it succeeds the breaker returns to CLOSED; if it fails it goes
          back to OPEN.
    """

    class CircuitOpenError(RuntimeError):
        """Raised when a call is attempted while the breaker is OPEN."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
    ) -> None:
        """Initialise the breaker.

        Args:
            failure_threshold: Consecutive failures before opening.
            recovery_timeout: Seconds to wait before probing.
            half_open_max_calls: How many calls to allow in HALF_OPEN.
        """
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_max_calls = half_open_max_calls

        self._state = State.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time: float = 0.0
        self._lock = asyncio.Lock()

    # ── Public API ─────────────────────────────────────────────

    @property
    def state(self) -> State:
        """Expose the current state (async-aware)."""
        return self._state

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute *func* through the circuit breaker.

        Raises:
            CircuitBreaker.CircuitOpenError: When the breaker is OPEN.
        """
        async with self._lock:
            self._maybe_transition()

            if self._state is State.OPEN:
                raise self.CircuitOpenError("Circuit breaker is OPEN")

            if self._state is State.HALF_OPEN:
                if self._half_open_calls >= self._half_open_max_calls:
                    raise self.CircuitOpenError("Circuit breaker is OPEN (half-open limit)")
                self._half_open_calls += 1

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
        except Exception:
            await self.record_failure()
            raise
        else:
            await self.record_success()
            return result

    async def record_success(self) -> None:
        """Record a successful operation."""
        async with self._lock:
            if self._state is State.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self._half_open_max_calls:
                    self._state = State.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    self._half_open_calls = 0
            elif self._state is State.CLOSED:
                self._failure_count = 0

    async def record_failure(self) -> None:
        """Record a failed operation."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()

            if self._state is State.HALF_OPEN:
                self._state = State.OPEN
                self._success_count = 0
                self._half_open_calls = 0
            elif self._state is State.CLOSED and self._failure_count >= self._failure_threshold:
                self._state = State.OPEN

    async def reset(self) -> None:
        """Manually reset the breaker to CLOSED."""
        async with self._lock:
            self._state = State.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0

    async def get_state(self) -> State:
        """Return the current state (async-aware, performs transition check)."""
        async with self._lock:
            self._maybe_transition()
            return self._state

    # ── Internals ──────────────────────────────────────────────

    def _maybe_transition(self) -> None:
        """Check for automatic OPEN → HALF_OPEN transition."""
        if self._state is State.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self._recovery_timeout:
                self._state = State.HALF_OPEN
                self._half_open_calls = 0
                self._success_count = 0
