"""Retry decorator with exponential backoff and jitter."""

from __future__ import annotations

import asyncio
import functools
import random
import time
from typing import Any, Callable, Optional, Sequence, Tuple, Type


def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_exceptions: Optional[Sequence[Type[Exception]]] = None,
) -> Callable:
    """Decorator that retries a function or coroutine on failure.

    Args:
        max_retries: Maximum number of retry attempts (not counting the
            original call).
        base_delay: Initial delay between retries in seconds.
        max_delay: Maximum delay cap in seconds.
        exponential_base: Base of the exponential back-off.
        jitter: Whether to add full jitter to the computed delay.
        retry_exceptions: Tuple of exception types to catch.  When ``None``
            all ``Exception`` subclasses are retried.

    Returns:
        Decorated callable.

    Usage::

        @retry(max_retries=5, base_delay=0.5)
        async def fetch(url: str) -> dict: ...

        @retry(max_retries=3, retry_exceptions=(ConnectionError,))
        def call_db() -> None: ...
    """

    def decorator(func: Callable) -> Callable:
        is_async = asyncio.iscoroutinefunction(func)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            exceptions_to_catch = (
                tuple(retry_exceptions) if retry_exceptions is not None else (Exception,)
            )
            last_exc: Optional[Exception] = None
            for attempt in range(1 + max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions_to_catch as exc:
                    last_exc = exc
                    if attempt == max_retries:
                        break
                    delay = _compute_delay(
                        attempt, base_delay, max_delay, exponential_base, jitter
                    )
                    await asyncio.sleep(delay)
            raise last_exc  # type: ignore[misc]

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            exceptions_to_catch = (
                tuple(retry_exceptions) if retry_exceptions is not None else (Exception,)
            )
            last_exc: Optional[Exception] = None
            for attempt in range(1 + max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions_to_catch as exc:
                    last_exc = exc
                    if attempt == max_retries:
                        break
                    delay = _compute_delay(
                        attempt, base_delay, max_delay, exponential_base, jitter
                    )
                    time.sleep(delay)
            raise last_exc  # type: ignore[misc]

        if is_async:
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    return decorator


def _compute_delay(
    attempt: int,
    base_delay: float,
    max_delay: float,
    exponential_base: float,
    jitter: bool,
) -> float:
    """Calculate the delay before the next retry."""
    delay = base_delay * (exponential_base ** attempt)
    delay = min(delay, max_delay)
    if jitter:
        delay = random.uniform(0, delay)
    return delay
