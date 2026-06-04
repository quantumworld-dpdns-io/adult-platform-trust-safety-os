"""Integration tests for admin API endpoints."""

from __future__ import annotations

import uuid

import pytest


pytestmark = [pytest.mark.integration]


async def _get_admin_token(async_client):
    resp = await async_client.post("/api/v1/auth/register", json={
        "email": "admin_user@example.com",
        "username": "admin_user",
        "password": "secureP@ss123",
    })
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_stats(async_client):
    admin_token = await _get_admin_token(async_client)
    resp = await async_client.get(
        "/api/v1/admin/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "total_users" in body
    assert "active_users" in body
    assert "banned_users" in body
    assert "verified_users" in body
    assert "mfa_enabled_users" in body
    assert isinstance(body["total_users"], int)
    assert body["total_users"] >= 1


@pytest.mark.asyncio
async def test_user_management(async_client):
    admin_token = await _get_admin_token(async_client)
    resp = await async_client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 1


@pytest.mark.asyncio
async def test_ban_user(async_client):
    admin_token = await _get_admin_token(async_client)
    reg = await async_client.post("/api/v1/auth/register", json={
        "email": "ban_target@example.com",
        "username": "ban_target",
        "password": "secureP@ss123",
    })
    target_token = reg.json()["access_token"]
    me = await async_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {target_token}"},
    )
    user_id = me.json()["id"]
    resp = await async_client.put(
        f"/api/v1/admin/users/{user_id}/ban",
        params={"reason": "Violation of terms"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "banned" in body["message"].lower()


@pytest.mark.asyncio
async def test_ban_nonexistent_user(async_client):
    admin_token = await _get_admin_token(async_client)
    fake_id = str(uuid.uuid4())
    resp = await async_client.put(
        f"/api/v1/admin/users/{fake_id}/ban",
        params={"reason": "Test"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_system_health(async_client):
    admin_token = await _get_admin_token(async_client)
    resp = await async_client.get(
        "/api/v1/admin/system-health",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body
    assert "version" in body
    assert "environment" in body
    assert "uptime_seconds" in body


@pytest.mark.asyncio
async def test_admin_stats_unauthorized(async_client):
    resp = await async_client.get("/api/v1/admin/stats")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_admin_audit_logs(async_client):
    admin_token = await _get_admin_token(async_client)
    resp = await async_client.get(
        "/api/v1/admin/audit-logs",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert isinstance(body["items"], list)
