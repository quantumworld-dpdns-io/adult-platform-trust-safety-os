"""Integration tests for consent API workflows."""

from __future__ import annotations

import pytest


pytestmark = [pytest.mark.integration]


async def _get_token(async_client):
    resp = await async_client.post("/api/v1/auth/register", json={
        "email": "consent_user@example.com",
        "username": "consent_user",
        "password": "secureP@ss123",
    })
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_grant_consent(async_client):
    token = await _get_token(async_client)
    resp = await async_client.post(
        "/api/v1/consent",
        params={"consent_type": "content", "granted": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    assert body["consent_type"] == "content"
    assert body["granted"] is True
    assert "granted_at" in body
    assert body["version"] == 1


@pytest.mark.asyncio
async def test_withdraw_consent(async_client):
    token = await _get_token(async_client, "withdraw@example.com", "withdraw")
    create_resp = await async_client.post(
        "/api/v1/consent",
        params={"consent_type": "analytics", "granted": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    consent_id = create_resp.json()["id"]
    resp = await async_client.put(
        f"/api/v1/consent/{consent_id}",
        params={"granted": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["granted"] is False
    assert body["withdrawn_at"] is not None
    assert body["version"] == 2


@pytest.mark.asyncio
async def test_consent_history(async_client):
    token = await _get_token(async_client, "history@example.com", "history")
    await async_client.post(
        "/api/v1/consent",
        params={"consent_type": "content", "granted": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    await async_client.post(
        "/api/v1/consent",
        params={"consent_type": "marketing", "granted": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await async_client.get(
        "/api/v1/consent/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] >= 2


@pytest.mark.asyncio
async def test_consent_history_filtered(async_client):
    token = await _get_token(async_client, "filter_hist@example.com", "filter_hist")
    await async_client.post(
        "/api/v1/consent",
        params={"consent_type": "content", "granted": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    await async_client.post(
        "/api/v1/consent",
        params={"consent_type": "marketing", "granted": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await async_client.get(
        "/api/v1/consent/history",
        params={"consent_type": "content"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    for item in body["items"]:
        assert item["consent_type"] == "content"


@pytest.mark.asyncio
async def test_list_consents(async_client):
    token = await _get_token(async_client, "listconsent@example.com", "listconsent")
    await async_client.post(
        "/api/v1/consent",
        params={"consent_type": "content", "granted": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await async_client.get(
        "/api/v1/consent",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_delete_consent(async_client):
    token = await _get_token(async_client, "delconsent@example.com", "delconsent")
    create_resp = await async_client.post(
        "/api/v1/consent",
        params={"consent_type": "content", "granted": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    consent_id = create_resp.json()["id"]
    resp = await async_client.delete(
        f"/api/v1/consent/{consent_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_consent_denied(async_client):
    token = await _get_token(async_client, "denied@example.com", "denied")
    resp = await async_client.post(
        "/api/v1/consent",
        params={"consent_type": "content", "granted": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["granted"] is False
