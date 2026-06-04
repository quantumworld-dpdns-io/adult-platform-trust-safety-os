"""Integration tests for moderation API endpoints."""

from __future__ import annotations

import uuid

import pytest


pytestmark = [pytest.mark.integration]


async def _get_admin_token(async_client):
    resp = await async_client.post("/api/v1/auth/register", json={
        "email": "mod_admin@example.com",
        "username": "mod_admin",
        "password": "secureP@ss123",
    })
    return resp.json()["access_token"]


async def _create_content(async_client, token):
    resp = await async_client.post(
        "/api/v1/content",
        json={"content_type": "TEXT", "raw_content": "Content for moderation"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_get_queue(async_client):
    admin_token = await _get_admin_token(async_client)
    resp = await async_client.get(
        "/api/v1/moderation/queue",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)


@pytest.mark.asyncio
async def test_approve(async_client):
    admin_token = await _get_admin_token(async_client)
    content_id = await _create_content(async_client, admin_token)
    resp = await async_client.post(
        f"/api/v1/moderation/{content_id}/approve",
        json={"decision": "approve", "reason": "Content is safe"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["status"] == "approved"


@pytest.mark.asyncio
async def test_reject(async_client):
    admin_token = await _get_admin_token(async_client)
    content_id = await _create_content(async_client, admin_token)
    resp = await async_client.post(
        f"/api/v1/moderation/{content_id}/reject",
        json={"decision": "reject", "reason": "Violates policy", "notes": "Contains prohibited content"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["status"] == "rejected"


@pytest.mark.asyncio
async def test_escalate(async_client):
    admin_token = await _get_admin_token(async_client)
    content_id = await _create_content(async_client, admin_token)
    resp = await async_client.post(
        f"/api/v1/moderation/{content_id}/escalate",
        json={"decision": "escalate", "reason": "Needs senior review"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["status"] == "escalated"


@pytest.mark.asyncio
async def test_moderate_not_found(async_client):
    admin_token = await _get_admin_token(async_client)
    fake_id = str(uuid.uuid4())
    resp = await async_client.post(
        f"/api/v1/moderation/{fake_id}/approve",
        json={"decision": "approve"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_stats(async_client):
    admin_token = await _get_admin_token(async_client)
    resp = await async_client.get(
        "/api/v1/moderation/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "pending" in body
    assert "in_review" in body
    assert "escalated" in body
    assert "approved" in body
    assert "rejected" in body
    assert "total_active" in body
    assert isinstance(body["pending"], int)
