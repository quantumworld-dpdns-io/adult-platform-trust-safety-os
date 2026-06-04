"""E2E tests: appeal flow."""

from __future__ import annotations

import pytest


pytestmark = [pytest.mark.e2e]


async def _get_token(async_client, email="appeal_e2e@example.com", username="appeal_e2e"):
    reg = await async_client.post("/api/v1/auth/register", json={
        "email": email,
        "username": username,
        "password": "secureP@ss123",
    })
    return reg.json()["access_token"]


@pytest.mark.asyncio
async def test_appeal_flow(async_client):
    user_token = await _get_token(async_client)
    auth = {"Authorization": f"Bearer {user_token}"}

    submit = await async_client.post(
        "/api/v1/content",
        json={"content_type": "TEXT", "raw_content": "Content for appeal test"},
        headers=auth,
    )
    assert submit.status_code == 201
    content_id = submit.json()["id"]

    reject_resp = await async_client.post(
        f"/api/v1/moderation/{content_id}/reject",
        json={
            "decision": "reject",
            "reason": "false_positive",
            "notes": "Incorrectly flagged as inappropriate",
        },
        headers=auth,
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "rejected"

    status = await async_client.get(
        f"/api/v1/content/{content_id}/moderation-status",
        headers=auth,
    )
    assert status.json()["status"] == "REJECTED"

    report_resp = await async_client.post(
        "/api/v1/reports",
        json={
            "target_content_id": content_id,
            "reason": "appeal",
            "description": "This content was wrongly rejected. It contains educational material about age verification systems and does not violate any community guidelines.",
        },
        headers=auth,
    )
    assert report_resp.status_code == 201
    report_id = report_resp.json()["id"]

    approve_resp = await async_client.post(
        f"/api/v1/moderation/{content_id}/approve",
        json={"decision": "approve", "reason": "appeal_upheld"},
        headers=auth,
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    resolve_resp = await async_client.put(
        f"/api/v1/reports/{report_id}/resolve",
        params={"resolution": "resolved"},
        headers=auth,
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["success"] is True

    final_status = await async_client.get(
        f"/api/v1/content/{content_id}/moderation-status",
        headers=auth,
    )
    assert final_status.status_code == 200
    assert final_status.json()["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_appeal_denied_flow(async_client):
    user_token = await _get_token(async_client, "appeal_denied@example.com", "appeal_denied")
    auth = {"Authorization": f"Bearer {user_token}"}

    submit = await async_client.post(
        "/api/v1/content",
        json={"content_type": "TEXT", "raw_content": "Content that will remain rejected"},
        headers=auth,
    )
    content_id = submit.json()["id"]

    await async_client.post(
        f"/api/v1/moderation/{content_id}/reject",
        json={"decision": "reject", "reason": "violates_guidelines"},
        headers=auth,
    )

    report = await async_client.post(
        "/api/v1/reports",
        json={
            "target_content_id": content_id,
            "reason": "appeal",
            "description": "I believe this content should not have been rejected because it is educational material.",
        },
        headers=auth,
    )
    report_id = report.json()["id"]

    dismiss = await async_client.put(
        f"/api/v1/reports/{report_id}/resolve",
        params={"resolution": "dismissed"},
        headers=auth,
    )
    assert dismiss.status_code == 200
    assert dismiss.json()["status"] == "dismissed"

    final = await async_client.get(
        f"/api/v1/content/{content_id}/moderation-status",
        headers=auth,
    )
    assert final.json()["status"] == "REJECTED"
