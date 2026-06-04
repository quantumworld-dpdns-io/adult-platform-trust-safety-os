"""Test helper functions."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from jose import jwt


def create_test_user(
    *,
    email: str = "test@example.com",
    username: str = "testuser",
    roles: list[str] | None = None,
    age_verified: bool = False,
    risk_score: float = 0.0,
):
    from src.core.user import User
    user = User()
    user.email = email
    user.username = username
    user.password_hash = "$argon2id$v=19$m=65536,t=3,p=4$fakehash"
    user.roles = roles or ["user"]
    user.age_verified = age_verified
    user.risk_score = risk_score
    user.is_active = True
    user.is_banned = False
    return user


def create_test_content(
    *,
    submitter_id: str | None = None,
    raw_content: str = "Test content for moderation",
    moderation_score: float | None = None,
):
    from src.moderation.content import Content, ContentStatus, ContentType
    content = Content()
    content.id = uuid.uuid4()
    content.submitter_id = submitter_id or str(uuid.uuid4())
    content.content_type = ContentType.TEXT
    content.raw_content = raw_content
    content.status = ContentStatus.PENDING
    content.moderation_score = moderation_score
    return content


def create_test_audit_event(
    *,
    actor_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict | None = None,
):
    from src.audit.models import ActionType, ActorType, AuditEvent
    event = AuditEvent()
    event.id = uuid.uuid4()
    event.timestamp = datetime.now(timezone.utc)
    event.actor_id = actor_id or str(uuid.uuid4())
    event.actor_type = ActorType.USER
    event.action = ActionType.CREATE
    event.resource_type = resource_type
    event.resource_id = resource_id
    event.details = details
    event.ip_address = "127.0.0.1"
    return event


def authenticate_request(headers: dict[str, str], token: str) -> dict[str, str]:
    headers["Authorization"] = f"Bearer {token}"
    return headers


def generate_test_jwt(
    subject: str = "test-user-id",
    *,
    roles: list[str] | None = None,
    secret: str = "test-secret-key-for-testing-only",
    algorithm: str = "HS256",
    expires_delta_minutes: int = 30,
) -> str:
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_delta_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    if roles is not None:
        payload["roles"] = roles
    return jwt.encode(payload, secret, algorithm=algorithm)


def assert_error_response(
    response_status: int,
    expected_status: int,
    body: dict,
    expected_error: str | None = None,
) -> None:
    assert response_status == expected_status, (
        f"Expected status {expected_status}, got {response_status}"
    )
    if expected_error:
        assert "detail" in body or "error" in body, (
            f"Expected error key in response body, got {body}"
        )


def assert_paginated_response(
    body: dict,
    *,
    expected_total: int | None = None,
    expected_page: int | None = None,
    expected_page_size: int | None = None,
    items_key: str = "items",
) -> None:
    assert items_key in body, f"Expected '{items_key}' key in response"
    assert isinstance(body[items_key], list), f"Expected '{items_key}' to be a list"

    if expected_total is not None:
        assert body.get("total") == expected_total, (
            f"Expected total={expected_total}, got {body.get('total')}"
        )
    if expected_page is not None:
        assert body.get("page") == expected_page, (
            f"Expected page={expected_page}, got {body.get('page')}"
        )
    if expected_page_size is not None:
        assert body.get("page_size") == expected_page_size, (
            f"Expected page_size={expected_page_size}, got {body.get('page_size')}"
        )
