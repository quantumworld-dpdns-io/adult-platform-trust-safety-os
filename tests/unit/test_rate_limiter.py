"""Tests for the SlidingWindowRateLimiter."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from src.security.api.rate_limiter import SlidingWindowRateLimiter


@pytest.fixture
def limiter():
    return SlidingWindowRateLimiter()


def test_acquire_first_request(limiter):
    limiter.configure_limits("api", max_requests=10, window_seconds=60)
    result = limiter.check_rate_limit("api", "user-1")
    assert result["allowed"] is True
    assert result["remaining"] == 9
    assert result["total"] == 10


def test_rate_limit_exceeded(limiter):
    limiter.configure_limits("api", max_requests=3, window_seconds=60)
    for _ in range(3):
        result = limiter.check_rate_limit("api", "user-1")
        assert result["allowed"] is True
    result = limiter.check_rate_limit("api", "user-1")
    assert result["allowed"] is False
    assert result["remaining"] == 0


def test_reset(limiter):
    limiter.configure_limits("api", max_requests=2, window_seconds=60)
    limiter.check_rate_limit("api", "user-1")
    limiter.check_rate_limit("api", "user-1")
    result = limiter.check_rate_limit("api", "user-1")
    assert result["allowed"] is False
    limiter.reset("api", "user-1")
    result = limiter.check_rate_limit("api", "user-1")
    assert result["allowed"] is True
    assert result["remaining"] == 1


def test_different_identifiers(limiter):
    limiter.configure_limits("api", max_requests=2, window_seconds=60)
    limiter.check_rate_limit("api", "user-1")
    limiter.check_rate_limit("api", "user-1")
    result = limiter.check_rate_limit("api", "user-1")
    assert result["allowed"] is False
    result = limiter.check_rate_limit("api", "user-2")
    assert result["allowed"] is True


def test_default_limits(limiter):
    result = limiter.check_rate_limit("unknown_key", "user-1")
    assert result["allowed"] is True
    assert result["total"] == 100


def test_get_remaining(limiter):
    limiter.configure_limits("api", max_requests=5, window_seconds=60)
    remaining = limiter.get_remaining("api", "user-1")
    assert remaining == 5
    limiter.check_rate_limit("api", "user-1")
    remaining = limiter.get_remaining("api", "user-1")
    assert remaining == 4


def test_get_usage_stats(limiter):
    limiter.configure_limits("api", max_requests=10, window_seconds=60)
    limiter.check_rate_limit("api", "user-1")
    stats = limiter.get_usage_stats("api", "user-1")
    assert stats["limit"] == 10
    assert stats["used"] == 1
    assert stats["remaining"] == 9
    assert stats["window"] == 60


def test_with_redis(redis_client):
    limiter = SlidingWindowRateLimiter(redis_client=redis_client)
    limiter.configure_limits("api", max_requests=3, window_seconds=60)
    for _ in range(3):
        result = limiter.check_rate_limit("api", "user-redis")
        assert result["allowed"] is True
    result = limiter.check_rate_limit("api", "user-redis")
    assert result["allowed"] is False
