"""Integration tests for user API endpoints."""

from __future__ import annotations

import uuid

import pytest


pytestmark = [pytest.mark.integration]


async def _register_and_get_token(async_client, email="user1@example.com", username="user1"):
    resp = await async_client.post("/api/v1/auth/register", json={
        "email": email,
        "username": username,
        "password": "secureP@ss123",
    })
    return resp.json()["access_token"]


async def _register_admin(async_client):
    token = await _register_and_get_token(async_client, "admin@example.com", "admin")
    return token


@pytest.mark.asyncio
async def test_create_user(async_client):
    token = await _register_and_get_token(async_client, "create@example.com", "createuser")
    resp = await async_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "create@example.com"
    assert body["username"] == "createuser"
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_get_user(async_client):
    token = await _register_and_get_token(async_client, "get@example.com", "getuser")
    me = await async_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    user_id = me.json()["id"]
    admin_token = await _register_admin(async_client)
    resp = await async_client.get(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == user_id


@pytest.mark.asyncio
async def test_update_user(async_client):
    token = await _register_and_get_token(async_client, "update@example.com", "updateuser")
    resp = await async_client.put(
        "/api/v1/users/me",
        json={"username": "updated_name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "updated_name"


@pytest.mark.asyncio
async def test_list_users(async_client):
    admin_token = await _register_admin(async_client)
    resp = await async_client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_delete_user(async_client):
    admin_token = await _register_admin(async_client)
    reg = await async_client.post("/api/v1/auth/register", json={
        "email": "delete_me@example.com",
        "username": "delete_me",
        "password": "secureP@ss123",
    })
    user_id = reg.json()["access_token"]
    me = await async_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {user_id}"},
    )
    target_id = me.json()["id"]
    resp = await async_client.delete(
        f"/api/v1/users/{target_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_get_nonexistent_user(async_client):
    admin_token = await _register_admin(async_client)
    fake_id = str(uuid.uuid4())
    resp = await async_client.get(
        f"/api/v1/users/{fake_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_verify_age(async_client):
    token = await _register_and_get_token(async_client, "age@example.com", "ageuser")
    me = await async_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    user_id = me.json()["id"]
    resp = await async_client.post(
        f"/api/v1/users/{user_id}/verify-age",
        json={
            "method": "document",
            "document_type": "passport",
            "document_data": "test-doc-data",
            "issued_country": "US",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body
    assert "age_confirmed" in body
    assert "confidence" in body


@pytest.mark.asyncio
async def test_verify_age_unauthorized(async_client):
    token1 = await _register_and_get_token(async_client, "age1@example.com", "age1")
    token2 = await _register_and_get_token(async_client, "age2@example.com", "age2")
    me2 = await async_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token2}"},
    )
    user_id2 = me2.json()["id"]
    resp = await async_client.post(
        f"/api/v1/users/{user_id2}/verify-age",
        json={
            "method": "document",
            "document_type": "passport",
            "document_data": "test-doc-data",
            "issued_country": "US",
        },
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert resp.status_code == 403
