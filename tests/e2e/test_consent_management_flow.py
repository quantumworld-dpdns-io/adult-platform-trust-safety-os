"""E2E tests: consent management flow."""

from __future__ import annotations

import pytest


pytestmark = [pytest.mark.e2e]


async def _get_token(async_client, email="consent_e2e@example.com", username="consent_e2e"):
    reg = await async_client.post("/api/v1/auth/register", json={
        "email": email,
        "username": username,
        "password": "secureP@ss123",
    })
    return reg.json()["access_token"]


@pytest.mark.asyncio
async def test_consent_grant_access_withdraw_restrict(async_client):
    token = await _get_token(async_client)
    auth = {"Authorization": f"Bearer {token}"}

    grant_resp = await async_client.post(
        "/api/v1/consent",
        params={"consent_type": "content", "granted": True},
        headers=auth,
    )
    assert grant_resp.status_code == 201
    consent_id = grant_resp.json()["id"]
    assert grant_resp.json()["granted"] is True

    history_resp = await async_client.get(
        "/api/v1/consent/history",
        params={"consent_type": "content"},
        headers=auth,
    )
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert history["total"] >= 1
    assert any(c["consent_type"] == "content" and c["granted"] for c in history["items"])

    content_resp = await async_client.post(
        "/api/v1/content",
        json={"content_type": "TEXT", "raw_content": "Content after consent"},
        headers=auth,
    )
    assert content_resp.status_code == 201

    withdraw_resp = await async_client.put(
        f"/api/v1/consent/{consent_id}",
        params={"granted": False},
        headers=auth,
    )
    assert withdraw_resp.status_code == 200
    assert withdraw_resp.json()["granted"] is False
    assert withdraw_resp.json()["withdrawn_at"] is not None

    updated_history = await async_client.get(
        "/api/v1/consent/history",
        params={"consent_type": "content"},
        headers=auth,
    )
    assert updated_history.status_code == 200
    items = updated_history.json()["items"]
    withdrawn = [c for c in items if not c["granted"]]
    assert len(withdrawn) >= 1


@pytest.mark.asyncio
async def test_consent_multiple_types_flow(async_client):
    token = await _get_token(async_client, "multi_consent@example.com", "multi_consent")
    auth = {"Authorization": f"Bearer {token}"}

    types = ["content", "analytics", "marketing", "third_party"]
    for ct in types:
        resp = await async_client.post(
            "/api/v1/consent",
            params={"consent_type": ct, "granted": True},
            headers=auth,
        )
        assert resp.status_code == 201

    list_resp = await async_client.get("/api/v1/consent", headers=auth)
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert body["total"] >= 4

    history = await async_client.get("/api/v1/consent/history", headers=auth)
    assert history.status_code == 200
    assert history.json()["total"] >= 4
