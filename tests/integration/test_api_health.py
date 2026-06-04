"""Integration tests for health check endpoints."""

from __future__ import annotations

import pytest


pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_liveness(async_client):
    resp = await async_client.get("/health/live")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "uptime" in body
    assert body["uptime"] >= 0


@pytest.mark.asyncio
async def test_readiness(async_client):
    resp = await async_client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("ok", "degraded")
    assert "version" in body
    assert "uptime" in body
    assert "checks" in body
    checks = body["checks"]
    assert "database" in checks
    for check in checks.values():
        assert "status" in check
        assert check["status"] in ("healthy", "unhealthy")


@pytest.mark.asyncio
async def test_startup(async_client):
    resp = await async_client.get("/health/startup")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "uptime" in body
