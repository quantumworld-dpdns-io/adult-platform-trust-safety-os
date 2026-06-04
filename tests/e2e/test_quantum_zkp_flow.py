"""E2E tests: quantum ZKP flow for age-gated content access."""

from __future__ import annotations

import pytest


pytestmark = [pytest.mark.e2e]


async def _get_admin_token(async_client):
    reg = await async_client.post("/api/v1/auth/register", json={
        "email": "zkp_e2e@example.com",
        "username": "zkp_e2e",
        "password": "secureP@ss123",
    })
    return reg.json()["access_token"]


@pytest.mark.asyncio
async def test_zkp_age_proof_flow(async_client):
    admin_token = await _get_admin_token(async_client)
    auth = {"Authorization": f"Bearer {admin_token}"}

    prove_resp = await async_client.post(
        "/api/v1/quantum/zkp/prove",
        json={
            "statement": {"claim": "age_over_18", "min_age": 18},
            "witness": {"birth_year": 1990, "birth_month": 5, "birth_day": 15},
        },
        headers=auth,
    )
    assert prove_resp.status_code == 200
    proof = prove_resp.json()
    assert "proof_id" in proof
    assert "proof" in proof

    verify_resp = await async_client.post(
        f"/api/v1/quantum/zkp/verify",
        params={"proof_id": proof["proof_id"]},
        json={"public_inputs": {"min_age": 18}},
        headers=auth,
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["valid"] is True

    pqc_resp = await async_client.get(
        "/api/v1/quantum/pqc/status",
        headers=auth,
    )
    assert pqc_resp.status_code == 200
    assert pqc_resp.json()["enabled"] is True

    content_resp = await async_client.post(
        "/api/v1/content",
        json={
            "content_type": "TEXT",
            "raw_content": "Age-gated content behind ZKP verification",
            "metadata": {"requires_age_proof": True, "minimum_age": 18},
        },
        headers=auth,
    )
    assert content_resp.status_code == 201
    content_id = content_resp.json()["id"]

    get_resp = await async_client.get(
        f"/api/v1/content/{content_id}",
        headers=auth,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == content_id


@pytest.mark.asyncio
async def test_zkp_consent_proof_flow(async_client):
    admin_token = await _get_admin_token(async_client)
    auth = {"Authorization": f"Bearer {admin_token}"}

    consent_resp = await async_client.post(
        "/api/v1/consent",
        params={"consent_type": "content", "granted": True},
        headers=auth,
    )
    assert consent_resp.status_code == 201

    prove_resp = await async_client.post(
        "/api/v1/quantum/zkp/prove",
        json={
            "statement": {"claim": "consent_given", "consent_type": "content"},
            "witness": {"consent_id": consent_resp.json()["id"]},
        },
        headers=auth,
    )
    assert prove_resp.status_code == 200

    verify_resp = await async_client.post(
        f"/api/v1/quantum/zkp/verify",
        params={"proof_id": prove_resp.json()["proof_id"]},
        json={"public_inputs": {"consent_type": "content"}},
        headers=auth,
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["valid"] is True


@pytest.mark.asyncio
async def test_zkp_invalid_proof_rejected(async_client):
    admin_token = await _get_admin_token(async_client)
    auth = {"Authorization": f"Bearer {admin_token}"}

    verify_resp = await async_client.post(
        "/api/v1/quantum/zkp/verify",
        params={"proof_id": "nonexistent-proof-id"},
        json={"public_inputs": {}},
        headers=auth,
    )
    assert verify_resp.status_code == 404
