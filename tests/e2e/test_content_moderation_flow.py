"""E2E tests: content moderation flow."""

from __future__ import annotations

import pytest


pytestmark = [pytest.mark.e2e]


async def _setup_user(async_client, email="mod_e2e@example.com", username="mod_e2e"):
    reg = await async_client.post("/api/v1/auth/register", json={
        "email": email,
        "username": username,
        "password": "secureP@ss123",
    })
    return reg.json()["access_token"]


@pytest.mark.asyncio
async def test_content_moderation_flow(async_client):
    user_token = await _setup_user(async_client)
    auth = {"Authorization": f"Bearer {user_token}"}

    submit_resp = await async_client.post(
        "/api/v1/content",
        json={
            "content_type": "TEXT",
            "raw_content": "E2E test content for full moderation pipeline",
            "metadata": {"source": "e2e_test"},
        },
        headers=auth,
    )
    assert submit_resp.status_code == 201
    content_id = submit_resp.json()["id"]
    assert submit_resp.json()["status"] == "PENDING"

    scan_resp = await async_client.post(
        f"/api/v1/content/{content_id}/scan",
        headers=auth,
    )
    assert scan_resp.status_code == 200
    scan = scan_resp.json()
    assert scan["content_id"] == content_id
    assert len(scan["classifications"]) > 0
    assert "overall_score" in scan

    status_resp = await async_client.get(
        f"/api/v1/content/{content_id}/moderation-status",
        headers=auth,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["content_id"] == content_id

    queue_resp = await async_client.get(
        "/api/v1/moderation/queue",
        headers=auth,
    )
    assert queue_resp.status_code == 200

    approve_resp = await async_client.post(
        f"/api/v1/moderation/{content_id}/approve",
        json={"decision": "approve", "reason": "Content passes all checks"},
        headers=auth,
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    final_status = await async_client.get(
        f"/api/v1/content/{content_id}/moderation-status",
        headers=auth,
    )
    assert final_status.status_code == 200
    assert final_status.json()["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_content_rejection_flow(async_client):
    user_token = await _setup_user(async_client, "rej_e2e@example.com", "rej_e2e")
    auth = {"Authorization": f"Bearer {user_token}"}

    submit = await async_client.post(
        "/api/v1/content",
        json={"content_type": "TEXT", "raw_content": "Content to reject"},
        headers=auth,
    )
    content_id = submit.json()["id"]

    reject_resp = await async_client.post(
        f"/api/v1/moderation/{content_id}/reject",
        json={
            "decision": "reject",
            "reason": "violates_community_guidelines",
            "notes": "Contains prohibited material",
        },
        headers=auth,
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_content_escalation_flow(async_client):
    user_token = await _setup_user(async_client, "esc_e2e@example.com", "esc_e2e")
    auth = {"Authorization": f"Bearer {user_token}"}

    submit = await async_client.post(
        "/api/v1/content",
        json={"content_type": "TEXT", "raw_content": "Borderline content"},
        headers=auth,
    )
    content_id = submit.json()["id"]

    esc_resp = await async_client.post(
        f"/api/v1/moderation/{content_id}/escalate",
        json={"decision": "escalate", "reason": "borderline_content"},
        headers=auth,
    )
    assert esc_resp.status_code == 200
    assert esc_resp.json()["status"] == "escalated"

    queue_resp = await async_client.get(
        "/api/v1/moderation/queue",
        headers=auth,
    )
    assert queue_resp.status_code == 200
    queue_items = queue_resp.json()
    ids = [item["id"] for item in queue_items]
    assert content_id in ids
