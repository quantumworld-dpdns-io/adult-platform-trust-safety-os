"""Integration tests for content API endpoints."""

from __future__ import annotations

import uuid

import pytest


pytestmark = [pytest.mark.integration]


async def _get_token(async_client, email="content_user@example.com", username="content_user"):
    resp = await async_client.post("/api/v1/auth/register", json={
        "email": email,
        "username": username,
        "password": "secureP@ss123",
    })
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_submit_content(async_client):
    token = await _get_token(async_client)
    resp = await async_client.post(
        "/api/v1/content",
        json={
            "content_type": "TEXT",
            "raw_content": "This is test content for moderation",
            "metadata": {"source": "test"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    assert body["content_type"] == "TEXT"
    assert body["status"] == "PENDING"
    assert body["raw_content"] == "This is test content for moderation"


@pytest.mark.asyncio
async def test_get_content(async_client):
    token = await _get_token(async_client, "get_content@example.com", "get_content")
    create_resp = await async_client.post(
        "/api/v1/content",
        json={"content_type": "TEXT", "raw_content": "Get me"},
        headers={"Authorization": f"Bearer {token}"},
    )
    content_id = create_resp.json()["id"]
    resp = await async_client.get(
        f"/api/v1/content/{content_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == content_id


@pytest.mark.asyncio
async def test_list_content(async_client):
    token = await _get_token(async_client, "list_content@example.com", "list_content")
    await async_client.post(
        "/api/v1/content",
        json={"content_type": "TEXT", "raw_content": "Item 1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await async_client.get(
        "/api/v1/content",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_scan_content(async_client):
    token = await _get_token(async_client, "scan_content@example.com", "scan_content")
    create_resp = await async_client.post(
        "/api/v1/content",
        json={"content_type": "TEXT", "raw_content": "Scan this content"},
        headers={"Authorization": f"Bearer {token}"},
    )
    content_id = create_resp.json()["id"]
    resp = await async_client.post(
        f"/api/v1/content/{content_id}/scan",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["content_id"] == content_id
    assert "classifications" in body
    assert "overall_score" in body
    assert "flagged" in body
    assert isinstance(body["classifications"], list)
    assert len(body["classifications"]) > 0


@pytest.mark.asyncio
async def test_delete_content(async_client):
    token = await _get_token(async_client, "del_content@example.com", "del_content")
    create_resp = await async_client.post(
        "/api/v1/content",
        json={"content_type": "TEXT", "raw_content": "Delete me"},
        headers={"Authorization": f"Bearer {token}"},
    )
    content_id = create_resp.json()["id"]
    resp = await async_client.delete(
        f"/api/v1/content/{content_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_content_not_found(async_client):
    token = await _get_token(async_client, "del_notfound@example.com", "del_notfound")
    fake_id = str(uuid.uuid4())
    resp = await async_client.delete(
        f"/api/v1/content/{fake_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_content_not_found(async_client):
    token = await _get_token(async_client, "get_notfound@example.com", "get_notfound")
    fake_id = str(uuid.uuid4())
    resp = await async_client.get(
        f"/api/v1/content/{fake_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_moderation_status(async_client):
    token = await _get_token(async_client, "modstat@example.com", "modstat")
    create_resp = await async_client.post(
        "/api/v1/content",
        json={"content_type": "TEXT", "raw_content": "Check status"},
        headers={"Authorization": f"Bearer {token}"},
    )
    content_id = create_resp.json()["id"]
    resp = await async_client.get(
        f"/api/v1/content/{content_id}/moderation-status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["content_id"] == content_id
    assert body["status"] == "PENDING"
