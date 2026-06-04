"""Tests for JWT token creation, verification, and decoding."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from jose import jwt

from tests.helpers import generate_test_jwt

SECRET = "test-jwt-secret-for-unit-tests"
ALGORITHM = "HS256"


def test_create_access_token():
    token = generate_test_jwt(subject="user-123", roles=["user"])
    assert isinstance(token, str)
    assert len(token) > 0
    parts = token.split(".")
    assert len(parts) == 3


def test_create_refresh_token():
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=7)
    payload = {
        "sub": "user-123",
        "iat": now,
        "exp": expire,
        "type": "refresh",
        "jti": "unique-id-123",
    }
    token = jwt.encode(payload, SECRET, algorithm=ALGORITHM)
    assert isinstance(token, str)
    decoded = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    assert decoded["type"] == "refresh"
    assert decoded["sub"] == "user-123"


def test_verify_valid_token():
    token = generate_test_jwt(subject="user-123", roles=["admin"])
    payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
    assert "admin" in payload["roles"]


def test_verify_expired_token():
    now = datetime.now(timezone.utc)
    expired_payload = {
        "sub": "user-123",
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),
        "type": "access",
    }
    token = jwt.encode(expired_payload, SECRET, algorithm=ALGORITHM)
    with pytest.raises(jose.ExpiredSignatureError):
        jwt.decode(token, SECRET, algorithms=[ALGORITHM])


def test_decode_token():
    token = generate_test_jwt(subject="decode-test", roles=["user", "moderator"])
    payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    assert payload["sub"] == "decode-test"
    assert set(payload["roles"]) == {"user", "moderator"}
    assert payload["type"] == "access"
    assert "iat" in payload
    assert "exp" in payload


def test_decode_with_wrong_secret():
    token = generate_test_jwt(subject="wrong-secret-test")
    with pytest.raises(jose.JWTError):
        jwt.decode(token, "wrong-secret", algorithms=[ALGORITHM])


def test_token_claims_structure():
    token = generate_test_jwt(subject="claims-test", roles=["user"])
    payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    assert "sub" in payload
    assert "iat" in payload
    assert "exp" in payload
    assert "type" in payload
    assert "roles" in payload


def test_decode_none_algorithm_rejected():
    token = jwt.encode({"sub": "test", "type": "access"}, SECRET, algorithm=ALGORITHM)
    with pytest.raises(Exception):
        jwt.decode(token, SECRET, algorithms=["none"])


def test_token_with_extra_claims():
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "extra-test",
        "iat": now,
        "exp": now + timedelta(minutes=30),
        "type": "access",
        "tenant_id": "tenant-abc",
        "custom_claim": "custom_value",
    }
    token = jwt.encode(payload, SECRET, algorithm=ALGORITHM)
    decoded = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    assert decoded["tenant_id"] == "tenant-abc"
    assert decoded["custom_claim"] == "custom_value"
