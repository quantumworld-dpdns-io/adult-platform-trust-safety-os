"""Integration tests for audit API endpoints."""

from __future__ import annotations

import uuid

import pytest


pytestmark = [pytest.mark.integration]


async def _get_admin_token(async_client):
    resp = await async_client.post("/api/v1/auth/register", json={
        "email": "audit_admin@example.com",
        "username": "audit_admin",
        "password": "secureP@ss123",
    })
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_get_events(async_client):
    admin_token = await _get_admin_token(async_client)
    resp = await async_client.get(
        "/api/v1/audit/events",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert "page" in body
    assert "per_page" in body
    assert isinstance(body["items"], list)


@pytest.mark.asyncio
async def test_get_events_with_filter(async_client):
    admin_token = await _get_admin_token(async_client)
    resp = await async_client.get(
        "/api/v1/audit/events",
        params={"action": "CREATE"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body


@pytest.mark.asyncio
async def test_verify_chain(async_client):
    admin_token = await _get_admin_token(async_client)
    resp = await async_client.get(
        "/api/v1/audit/verify",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "valid" in body
    assert "total_events" in body
    assert "verified_events" in body
    assert "chain_valid" in body
    assert isinstance(body["valid"], bool)


@pytest.mark.asyncio
async def test_export(async_client):
    admin_token = await _get_admin_token(async_client)
    resp = await async_client.get(
        "/api/v1/audit/export",
        params={"format": "json"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "format" in body
    assert "count" in body
    assert "events" in body
    assert body["format"] == "json"
    assert isinstance(body["events"], list)


@pytest.mark.asyncio
async def test_stats(async_client):
    admin_token = await _get_admin_token(async_client)
    resp = await async_client.get(
        "/api/v1/audit/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "total_events" in body
    assert "events_today" in body
    assert "events_by_action" in body
    assert "events_by_actor_type" in body
    assert "unique_actors" in body
    assert "average_events_per_day" in body
    assert isinstance(body["events_by_action"], dict)
    assert isinstance(body["events_by_actor_type"], dict)


@pytest.mark.asyncio
async def test_events_unauthorized(async_client):
    resp = await async_client.get("/api/v1/audit/events")
    assert resp.status_code in (401, 403)
