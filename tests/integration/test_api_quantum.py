"""Integration tests for quantum API endpoints."""

from __future__ import annotations

import pytest


pytestmark = [pytest.mark.integration]


async def _get_admin_token(async_client):
    resp = await async_client.post("/api/v1/auth/register", json={
        "email": "quantum_admin@example.com",
        "username": "quantum_admin",
        "password": "secureP@ss123",
    })
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_circuit_execute(async_client):
    admin_token = await _get_admin_token(async_client)
    resp = await async_client.post(
        "/api/v1/quantum/circuit/execute",
        json={
            "circuit_type": "bell_state",
            "num_qubits": 2,
            "shots": 1024,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "circuit_id" in body
    assert body["status"] == "running"
    assert "message" in body


@pytest.mark.asyncio
async def test_circuit_status(async_client):
    admin_token = await _get_admin_token(async_client)
    exec_resp = await async_client.post(
        "/api/v1/quantum/circuit/execute",
        json={"circuit_type": "bell_state", "num_qubits": 2},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    circuit_id = exec_resp.json()["circuit_id"]
    resp = await async_client.get(
        f"/api/v1/quantum/circuit/{circuit_id}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == circuit_id
    assert body["status"] == "running"


@pytest.mark.asyncio
async def test_zkp_prove(async_client):
    admin_token = await _get_admin_token(async_client)
    resp = await async_client.post(
        "/api/v1/quantum/zkp/prove",
        json={
            "statement": {"claim": "age_over_18", "min_age": 18},
            "witness": {"birth_year": 1990},
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "proof_id" in body
    assert "proof" in body
    assert body["algorithm"] == "groth16"
    assert "created_at" in body


@pytest.mark.asyncio
async def test_zkp_verify(async_client):
    admin_token = await _get_admin_token(async_client)
    prove_resp = await async_client.post(
        "/api/v1/quantum/zkp/prove",
        json={
            "statement": {"claim": "age_over_18"},
            "witness": {"birth_year": 1990},
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    proof_id = prove_resp.json()["proof_id"]
    resp = await async_client.post(
        f"/api/v1/quantum/zkp/verify",
        params={"proof_id": proof_id},
        json={"public_inputs": {"min_age": 18}},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["proof_id"] == proof_id
    assert body["valid"] is True
    assert "verified_at" in body


@pytest.mark.asyncio
async def test_zkp_verify_not_found(async_client):
    admin_token = await _get_admin_token(async_client)
    resp = await async_client.post(
        "/api/v1/quantum/zkp/verify",
        params={"proof_id": "nonexistent-proof-id"},
        json={"public_inputs": {}},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_pqc_status(async_client):
    admin_token = await _get_admin_token(async_client)
    resp = await async_client.get(
        "/api/v1/quantum/pqc/status",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is True
    assert "algorithms" in body
    assert body["algorithms"]["key_exchange"] == "ML-KEM-768"
    assert body["algorithms"]["signature"] == "ML-DSA-65"
    assert body["algorithms"]["hash"] == "SHA3-256"
    assert body["hybrid_mode"] is True
    assert body["status"] == "operational"


@pytest.mark.asyncio
async def test_quantum_unauthorized(async_client):
    resp = await async_client.get("/api/v1/quantum/pqc/status")
    assert resp.status_code in (401, 403)
