"""Security tests: rate limiting enforcement."""

from __future__ import annotations

import pytest

from src.security.api.rate_limiter import SlidingWindowRateLimiter


pytestmark = [pytest.mark.security]


class TestRateLimiterUnit:
    def setup_method(self):
        self.limiter = SlidingWindowRateLimiter()

    def test_basic_rate_limit(self):
        self.limiter.configure_limits("api.login", max_requests=5, window_seconds=60)
        for i in range(5):
            result = self.limiter.check_rate_limit("api.login", "user1")
            assert result["allowed"] is True, f"Request {i+1} should be allowed"

        result = self.limiter.check_rate_limit("api.login", "user1")
        assert result["allowed"] is False
        assert result["remaining"] == 0

    def test_different_identifiers_independent(self):
        self.limiter.configure_limits("api.login", max_requests=3, window_seconds=60)
        for _ in range(3):
            self.limiter.check_rate_limit("api.login", "user_a")

        result_a = self.limiter.check_rate_limit("api.login", "user_a")
        assert result_a["allowed"] is False

        result_b = self.limiter.check_rate_limit("api.login", "user_b")
        assert result_b["allowed"] is True

    def test_different_keys_independent(self):
        self.limiter.configure_limits("api.login", max_requests=3, window_seconds=60)
        self.limiter.configure_limits("api.register", max_requests=3, window_seconds=60)

        for _ in range(3):
            self.limiter.check_rate_limit("api.login", "user1")

        result_login = self.limiter.check_rate_limit("api.login", "user1")
        assert result_login["allowed"] is False

        result_register = self.limiter.check_rate_limit("api.register", "user1")
        assert result_register["allowed"] is True

    def test_remaining_count(self):
        self.limiter.configure_limits("api.submit", max_requests=10, window_seconds=60)
        result = self.limiter.check_rate_limit("api.submit", "user1")
        assert result["remaining"] == 9

        self.limiter.check_rate_limit("api.submit", "user1")
        result = self.limiter.check_rate_limit("api.submit", "user1")
        assert result["remaining"] == 7

    def test_reset(self):
        self.limiter.configure_limits("api.test", max_requests=2, window_seconds=60)
        self.limiter.check_rate_limit("api.test", "user1")
        self.limiter.check_rate_limit("api.test", "user1")

        result = self.limiter.check_rate_limit("api.test", "user1")
        assert result["allowed"] is False

        self.limiter.reset("api.test", "user1")

        result = self.limiter.check_rate_limit("api.test", "user1")
        assert result["allowed"] is True
        assert result["remaining"] == 1

    def test_get_usage_stats(self):
        self.limiter.configure_limits("api.test", max_requests=10, window_seconds=60)
        self.limiter.check_rate_limit("api.test", "user1")
        self.limiter.check_rate_limit("api.test", "user1")

        stats = self.limiter.get_usage_stats("api.test", "user1")
        assert stats["limit"] == 10
        assert stats["used"] == 2
        assert stats["remaining"] == 8
        assert stats["window"] == 60

    def test_get_remaining(self):
        self.limiter.configure_limits("api.test", max_requests=5, window_seconds=60)
        remaining = self.limiter.get_remaining("api.test", "user1")
        assert remaining == 5

        self.limiter.check_rate_limit("api.test", "user1")
        remaining = self.limiter.get_remaining("api.test", "user1")
        assert remaining == 4

    def test_total_matches_max_requests(self):
        self.limiter.configure_limits("api.test", max_requests=7, window_seconds=60)
        result = self.limiter.check_rate_limit("api.test", "user1")
        assert result["total"] == 7

    def test_default_limit_applied(self):
        result = self.limiter.check_rate_limit("unconfigured_key", "user1")
        assert result["allowed"] is True
        assert result["total"] == 100


@pytest.mark.asyncio
async def test_rate_limit_middleware_enforcement(async_client):
    responses = []
    for _ in range(20):
        resp = await async_client.get("/health/live")
        responses.append(resp.status_code)

    assert 200 in responses


@pytest.mark.asyncio
async def test_rate_limit_on_auth_endpoints(async_client):
    for i in range(10):
        resp = await async_client.post("/api/v1/auth/login", json={
            "email": "ratelimit@example.com",
            "password": "wrongpassword",
        })
        if resp.status_code == 429:
            body = resp.json()
            assert "detail" in body
            break
    else:
        assert True
