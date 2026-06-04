"""E2E tests: full user registration flow."""

from __future__ import annotations

import pytest


pytestmark = [pytest.mark.e2e]


@pytest.mark.asyncio
async def test_full_registration_flow(async_client):
    reg_resp = await async_client.post("/api/v1/auth/register", json={
        "email": "e2e_reg@example.com",
        "username": "e2e_reg_user",
        "password": "secureP@ss123",
    })
    assert reg_resp.status_code == 201
    tokens = reg_resp.json()
    access = tokens["access_token"]
    auth_headers = {"Authorization": f"Bearer {access}"}

    login_resp = await async_client.post("/api/v1/auth/login", json={
        "email": "e2e_reg@example.com",
        "password": "secureP@ss123",
    })
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()

    me_resp = await async_client.get("/api/v1/users/me", headers=auth_headers)
    assert me_resp.status_code == 200
    user = me_resp.json()
    assert user["email"] == "e2e_reg@example.com"
    assert user["username"] == "e2e_reg_user"
    assert user["age_verified"] is False

    profile_resp = await async_client.put(
        "/api/v1/users/me",
        json={"profile": {"display_name": "E2E User", "bio": "Test user"}},
        headers=auth_headers,
    )
    assert profile_resp.status_code == 200
    assert profile_resp.json()["profile"]["display_name"] == "E2E User"

    age_resp = await async_client.post(
        f"/api/v1/users/{user['id']}/verify-age",
        json={
            "method": "document",
            "document_type": "passport",
            "document_data": "e2e-test-doc-data",
            "issued_country": "US",
        },
        headers=auth_headers,
    )
    assert age_resp.status_code == 200
    age_body = age_resp.json()
    assert "age_confirmed" in age_body
    assert "status" in age_body

    final_me = await async_client.get("/api/v1/users/me", headers=auth_headers)
    assert final_me.status_code == 200
    final_user = final_me.json()
    assert final_user["profile"]["display_name"] == "E2E User"


@pytest.mark.asyncio
async def test_registration_login_logout_cycle(async_client):
    reg_resp = await async_client.post("/api/v1/auth/register", json={
        "email": "cycle@example.com",
        "username": "cycle_user",
        "password": "secureP@ss123",
    })
    assert reg_resp.status_code == 201
    token = reg_resp.json()["access_token"]

    me = await async_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200

    logout = await async_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout.status_code == 200

    login = await async_client.post("/api/v1/auth/login", json={
        "email": "cycle@example.com",
        "password": "secureP@ss123",
    })
    assert login.status_code == 200
    assert "access_token" in login.json()
