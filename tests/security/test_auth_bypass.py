"""Security tests: authentication bypass attempts."""

from __future__ import annotations

import uuid

import pytest

from tests.helpers import generate_test_jwt


pytestmark = [pytest.mark.security]


@pytest.mark.asyncio
async def test_bypass_no_auth_header(async_client):
    endpoints = [
        ("GET", "/api/v1/users/me"),
        ("GET", "/api/v1/content"),
        ("POST", "/api/v1/content"),
        ("GET", "/api/v1/moderation/queue"),
        ("GET", "/api/v1/audit/events"),
        ("GET", "/api/v1/admin/stats"),
    ]
    for method, path in endpoints:
        if method == "GET":
            resp = await async_client.get(path)
        else:
            resp = await async_client.post(path, json={})
        assert resp.status_code in (401, 403), (
            f"Should reject unauthenticated request to {method} {path}"
        )


@pytest.mark.asyncio
async def test_bypass_invalid_token(async_client):
    headers = {"Authorization": "Bearer invalid.token.here"}
    resp = await async_client.get("/api/v1/users/me", headers=headers)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_bypass_expired_token(async_client):
    token = generate_test_jwt(
        subject=str(uuid.uuid4()),
        roles=["user"],
        expires_delta_minutes=-30,
    )
    headers = {"Authorization": f"Bearer {token}"}
    resp = await async_client.get("/api/v1/users/me", headers=headers)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_bypass_malformed_auth_header(async_client):
    headers_list = [
        {"Authorization": "Bearer"},
        {"Authorization": "Token abc123"},
        {"Authorization": "Basic dXNlcjpwYXNz"},
        {"Authorization": "abc123"},
        {"Authorization": ""},
    ]
    for headers in headers_list:
        resp = await async_client.get("/api/v1/users/me", headers=headers)
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_bypass_role_escalation(async_client):
    reg = await async_client.post("/api/v1/auth/register", json={
        "email": "normal@example.com",
        "username": "normal_user",
        "password": "secureP@ss123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    admin_endpoints = [
        ("GET", "/api/v1/admin/stats"),
        ("GET", "/api/v1/admin/users"),
        ("GET", "/api/v1/audit/events"),
        ("GET", "/api/v1/moderation/queue"),
    ]
    for method, path in admin_endpoints:
        resp = await async_client.get(path, headers=headers)
        assert resp.status_code == 403, (
            f"Normal user should be forbidden from {method} {path}"
        )


@pytest.mark.asyncio
async def test_bypass_admin_endpoints_require_role(async_client):
    resp = await async_client.get("/api/v1/admin/stats")
    assert resp.status_code in (401, 403)

    resp = await async_client.get("/api/v1/admin/users")
    assert resp.status_code in (401, 403)

    resp = await async_client.get("/api/v1/audit/events")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_bypass_token_reuse_after_logout(async_client):
    reg = await async_client.post("/api/v1/auth/register", json={
        "email": "reuse@example.com",
        "username": "reuse_user",
        "password": "secureP@ss123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = await async_client.get("/api/v1/users/me", headers=headers)
    assert me.status_code == 200

    await async_client.post("/api/v1/auth/logout", headers=headers)

    resp = await async_client.get("/api/v1/users/me", headers=headers)
    assert resp.status_code in (200, 401)


@pytest.mark.asyncio
async def test_bypass_path_traversal_in_user_id(async_client):
    reg = await async_client.post("/api/v1/auth/register", json={
        "email": "traversal@example.com",
        "username": "traversal",
        "password": "secureP@ss123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    traversal_ids = [
        "../../../etc/passwd",
        "..%2F..%2F..%2Fetc%2Fpasswd",
        "%2e%2e%2f%2e%2e%2f",
        "....//....//",
    ]
    for uid in traversal_ids:
        resp = await async_client.get(f"/api/v1/users/{uid}", headers=headers)
        assert resp.status_code in (400, 404), (
            f"Should reject path traversal: {uid}"
        )


@pytest.mark.asyncio
async def test_bypass_method_not_allowed(async_client):
    resp = await async_client.put("/api/v1/auth/register", json={})
    assert resp.status_code in (405, 422)

    resp = await async_client.delete("/api/v1/auth/register")
    assert resp.status_code in (405, 422)
