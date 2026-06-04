"""Integration tests for reports API endpoints."""

from __future__ import annotations

import uuid

import pytest


pytestmark = [pytest.mark.integration]


async def _get_token(async_client, email="reporter@example.com", username="reporter"):
    resp = await async_client.post("/api/v1/auth/register", json={
        "email": email,
        "username": username,
        "password": "secureP@ss123",
    })
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_create_report(async_client):
    token = await _get_token(async_client)
    resp = await async_client.post(
        "/api/v1/reports",
        json={
            "target_content_id": str(uuid.uuid4()),
            "reason": "spam",
            "description": "This is spam content that should be removed",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    assert body["reason"] == "spam"
    assert body["status"] == "PENDING"


@pytest.mark.asyncio
async def test_create_report_user_target(async_client):
    token = await _get_token(async_client, "reporter2@example.com", "reporter2")
    resp = await async_client.post(
        "/api/v1/reports",
        json={
            "target_user_id": str(uuid.uuid4()),
            "reason": "harassment",
            "description": "User is harassing other users",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["reason"] == "harassment"
    assert body["target_user_id"] is not None


@pytest.mark.asyncio
async def test_list_reports(async_client):
    token = await _get_token(async_client, "listreporter@example.com", "listreporter")
    await async_client.post(
        "/api/v1/reports",
        json={
            "target_content_id": str(uuid.uuid4()),
            "reason": "spam",
            "description": "Spam content",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await async_client.get(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_resolve_report(async_client):
    token = await _get_token(async_client, "resolveme@example.com", "resolveme")
    create_resp = await async_client.post(
        "/api/v1/reports",
        json={
            "target_content_id": str(uuid.uuid4()),
            "reason": "spam",
            "description": "Spam to resolve",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    report_id = create_resp.json()["id"]
    resp = await async_client.put(
        f"/api/v1/reports/{report_id}/resolve",
        params={"resolution": "resolved"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["status"] == "resolved"


@pytest.mark.asyncio
async def test_dismiss_report(async_client):
    token = await _get_token(async_client, "dismiss@example.com", "dismiss")
    create_resp = await async_client.post(
        "/api/v1/reports",
        json={
            "target_content_id": str(uuid.uuid4()),
            "reason": "spam",
            "description": "False report",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    report_id = create_resp.json()["id"]
    resp = await async_client.put(
        f"/api/v1/reports/{report_id}/resolve",
        params={"resolution": "dismissed"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["status"] == "dismissed"


@pytest.mark.asyncio
async def test_resolve_report_invalid_resolution(async_client):
    token = await _get_token(async_client, "invalidres@example.com", "invalidres")
    create_resp = await async_client.post(
        "/api/v1/reports",
        json={
            "target_content_id": str(uuid.uuid4()),
            "reason": "spam",
            "description": "Content",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    report_id = create_resp.json()["id"]
    resp = await async_client.put(
        f"/api/v1/reports/{report_id}/resolve",
        params={"resolution": "invalid_resolution"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_report_not_found(async_client):
    token = await _get_token(async_client, "notfoundrpt@example.com", "notfoundrpt")
    fake_id = str(uuid.uuid4())
    resp = await async_client.get(
        f"/api/v1/reports/{fake_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
