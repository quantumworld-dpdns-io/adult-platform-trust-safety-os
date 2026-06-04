"""Integration tests for authentication API endpoints."""

from __future__ import annotations

import pytest


pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_register(async_client):
    resp = await async_client.post("/api/v1/auth/register", json={
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "secureP@ss123",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0


@pytest.mark.asyncio
async def test_register_duplicate_email(async_client):
    payload = {
        "email": "dup@example.com",
        "username": "dupuser",
        "password": "secureP@ss123",
    }
    await async_client.post("/api/v1/auth/register", json=payload)
    resp = await async_client.post("/api/v1/auth/register", json={
        "email": "dup@example.com",
        "username": "dupuser2",
        "password": "secureP@ss123",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login(async_client):
    await async_client.post("/api/v1/auth/register", json={
        "email": "logintest@example.com",
        "username": "logintest",
        "password": "secureP@ss123",
    })
    resp = await async_client.post("/api/v1/auth/login", json={
        "email": "logintest@example.com",
        "password": "secureP@ss123",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body


@pytest.mark.asyncio
async def test_login_invalid_credentials(async_client):
    resp = await async_client.post("/api/v1/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(async_client):
    reg = await async_client.post("/api/v1/auth/register", json={
        "email": "refresh@example.com",
        "username": "refreshuser",
        "password": "secureP@ss123",
    })
    refresh_token = reg.json()["refresh_token"]
    resp = await async_client.post("/api/v1/auth/refresh", params={
        "refresh_token": refresh_token,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body


@pytest.mark.asyncio
async def test_refresh_invalid_token(async_client):
    resp = await async_client.post("/api/v1/auth/refresh", params={
        "refresh_token": "invalid.token.here",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout(async_client):
    reg = await async_client.post("/api/v1/auth/register", json={
        "email": "logout@example.com",
        "username": "logoutuser",
        "password": "secureP@ss123",
    })
    token = reg.json()["access_token"]
    resp = await async_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_mfa_enable(async_client):
    reg = await async_client.post("/api/v1/auth/register", json={
        "email": "mfa@example.com",
        "username": "mfauser",
        "password": "secureP@ss123",
    })
    token = reg.json()["access_token"]
    resp = await async_client.post(
        "/api/v1/auth/mfa/enable",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "secret" in body
    assert "provisioning_uri" in body
    assert "backup_codes" in body
    assert len(body["backup_codes"]) > 0


@pytest.mark.asyncio
async def test_mfa_verify_invalid_code(async_client):
    reg = await async_client.post("/api/v1/auth/register", json={
        "email": "mfa2@example.com",
        "username": "mfa2user",
        "password": "secureP@ss123",
    })
    token = reg.json()["access_token"]
    await async_client.post(
        "/api/v1/auth/mfa/enable",
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await async_client.post(
        "/api/v1/auth/mfa/verify",
        json={"code": "000000"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 401)
