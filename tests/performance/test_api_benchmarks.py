"""API benchmark tests measuring latency for each endpoint category."""

from __future__ import annotations

import time

import pytest


pytestmark = [pytest.mark.performance, pytest.mark.slow]


async def _get_token(async_client):
    resp = await async_client.post("/api/v1/auth/register", json={
        "email": "bench@example.com",
        "username": "bench_user",
        "password": "secureP@ss123",
    })
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_benchmark_health_endpoints(async_client):
    start = time.perf_counter()
    for _ in range(10):
        await async_client.get("/health/live")
    elapsed = time.perf_counter() - start
    avg_ms = (elapsed / 10) * 1000
    assert avg_ms < 500, f"Health endpoint avg latency too high: {avg_ms:.1f}ms"


@pytest.mark.asyncio
async def test_benchmark_auth_endpoints(async_client):
    start = time.perf_counter()
    for i in range(5):
        await async_client.post("/api/v1/auth/register", json={
            "email": f"bench_auth_{i}@example.com",
            "username": f"bench_auth_{i}",
            "password": "secureP@ss123",
        })
    elapsed = time.perf_counter() - start
    avg_ms = (elapsed / 5) * 1000
    assert avg_ms < 2000, f"Auth register avg latency too high: {avg_ms:.1f}ms"


@pytest.mark.asyncio
async def test_benchmark_content_endpoints(async_client):
    token = await _get_token(async_client)
    auth = {"Authorization": f"Bearer {token}"}

    content_ids = []
    start = time.perf_counter()
    for i in range(5):
        resp = await async_client.post(
            "/api/v1/content",
            json={"content_type": "TEXT", "raw_content": f"Benchmark content {i}"},
            headers=auth,
        )
        if resp.status_code == 201:
            content_ids.append(resp.json()["id"])
    create_elapsed = time.perf_counter() - start
    create_avg = (create_elapsed / 5) * 1000

    start = time.perf_counter()
    for cid in content_ids:
        await async_client.get(f"/api/v1/content/{cid}", headers=auth)
    get_elapsed = time.perf_counter() - start
    get_avg = (get_elapsed / max(len(content_ids), 1)) * 1000

    assert create_avg < 2000, f"Content create avg latency too high: {create_avg:.1f}ms"
    assert get_avg < 1000, f"Content get avg latency too high: {get_avg:.1f}ms"


@pytest.mark.asyncio
async def test_benchmark_moderation_endpoints(async_client):
    token = await _get_token(async_client)
    auth = {"Authorization": f"Bearer {token}"}

    content_ids = []
    for i in range(3):
        resp = await async_client.post(
            "/api/v1/content",
            json={"content_type": "TEXT", "raw_content": f"Mod bench {i}"},
            headers=auth,
        )
        if resp.status_code == 201:
            content_ids.append(resp.json()["id"])

    start = time.perf_counter()
    for cid in content_ids:
        await async_client.post(
            f"/api/v1/moderation/{cid}/approve",
            json={"decision": "approve"},
            headers=auth,
        )
    elapsed = time.perf_counter() - start
    avg_ms = (elapsed / max(len(content_ids), 1)) * 1000
    assert avg_ms < 2000, f"Moderation approve avg latency too high: {avg_ms:.1f}ms"

    start = time.perf_counter()
    await async_client.get("/api/v1/moderation/queue", headers=auth)
    queue_elapsed = time.perf_counter() - start
    assert queue_elapsed < 1.0, f"Moderation queue latency too high: {queue_elapsed * 1000:.1f}ms"


@pytest.mark.asyncio
async def test_benchmark_audit_endpoints(async_client):
    token = await _get_token(async_client)
    auth = {"Authorization": f"Bearer {token}"}

    start = time.perf_counter()
    await async_client.get("/api/v1/audit/events", headers=auth)
    events_elapsed = time.perf_counter() - start

    start = time.perf_counter()
    await async_client.get("/api/v1/audit/stats", headers=auth)
    stats_elapsed = time.perf_counter() - start

    assert events_elapsed < 2.0, f"Audit events latency too high: {events_elapsed * 1000:.1f}ms"
    assert stats_elapsed < 2.0, f"Audit stats latency too high: {stats_elapsed * 1000:.1f}ms"


@pytest.mark.asyncio
async def test_benchmark_quantum_endpoints(async_client):
    token = await _get_token(async_client)
    auth = {"Authorization": f"Bearer {token}"}

    start = time.perf_counter()
    await async_client.get("/api/v1/quantum/pqc/status", headers=auth)
    pqc_elapsed = time.perf_counter() - start
    assert pqc_elapsed < 1.0, f"PQC status latency too high: {pqc_elapsed * 1000:.1f}ms"

    start = time.perf_counter()
    resp = await async_client.post(
        "/api/v1/quantum/zkp/prove",
        json={"statement": {"claim": "age_over_18"}, "witness": {"age": 30}},
        headers=auth,
    )
    prove_elapsed = time.perf_counter() - start
    assert prove_elapsed < 2.0, f"ZKP prove latency too high: {prove_elapsed * 1000:.1f}ms"

    if resp.status_code == 200:
        proof_id = resp.json()["proof_id"]
        start = time.perf_counter()
        await async_client.post(
            f"/api/v1/quantum/zkp/verify",
            params={"proof_id": proof_id},
            json={"public_inputs": {"min_age": 18}},
            headers=auth,
        )
        verify_elapsed = time.perf_counter() - start
        assert verify_elapsed < 2.0, f"ZKP verify latency too high: {verify_elapsed * 1000:.1f}ms"


@pytest.mark.asyncio
async def test_benchmark_consent_endpoints(async_client):
    token = await _get_token(async_client)
    auth = {"Authorization": f"Bearer {token}"}

    start = time.perf_counter()
    for _ in range(5):
        await async_client.post(
            "/api/v1/consent",
            params={"consent_type": "content", "granted": True},
            headers=auth,
        )
    elapsed = time.perf_counter() - start
    avg_ms = (elapsed / 5) * 1000
    assert avg_ms < 1500, f"Consent create avg latency too high: {avg_ms:.1f}ms"

    start = time.perf_counter()
    await async_client.get("/api/v1/consent/history", headers=auth)
    history_elapsed = time.perf_counter() - start
    assert history_elapsed < 1.0, f"Consent history latency too high: {history_elapsed * 1000:.1f}ms"


@pytest.mark.asyncio
async def test_benchmark_admin_endpoints(async_client):
    token = await _get_token(async_client)
    auth = {"Authorization": f"Bearer {token}"}

    start = time.perf_counter()
    await async_client.get("/api/v1/admin/stats", headers=auth)
    stats_elapsed = time.perf_counter() - start

    start = time.perf_counter()
    await async_client.get("/api/v1/admin/users", headers=auth)
    users_elapsed = time.perf_counter() - start

    assert stats_elapsed < 1.0, f"Admin stats latency too high: {stats_elapsed * 1000:.1f}ms"
    assert users_elapsed < 1.0, f"Admin users latency too high: {users_elapsed * 1000:.1f}ms"


@pytest.mark.asyncio
async def test_benchmark_reports_endpoints(async_client):
    token = await _get_token(async_client)
    auth = {"Authorization": f"Bearer {token}"}

    report_ids = []
    start = time.perf_counter()
    for i in range(5):
        resp = await async_client.post(
            "/api/v1/reports",
            json={
                "reason": "spam",
                "description": f"Benchmark report {i}",
            },
            headers=auth,
        )
        if resp.status_code == 201:
            report_ids.append(resp.json()["id"])
    create_elapsed = time.perf_counter() - start
    create_avg = (create_elapsed / 5) * 1000

    start = time.perf_counter()
    await async_client.get("/api/v1/reports", headers=auth)
    list_elapsed = time.perf_counter() - start

    assert create_avg < 2000, f"Report create avg latency too high: {create_avg:.1f}ms"
    assert list_elapsed < 1.0, f"Report list latency too high: {list_elapsed * 1000:.1f}ms"
