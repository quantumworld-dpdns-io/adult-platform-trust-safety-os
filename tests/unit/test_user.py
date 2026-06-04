"""Tests for the User ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from src.core.user import User


def _make_user(**kwargs):
    from datetime import datetime, timezone
    defaults = {
        "id": uuid.uuid4(),
        "email": "alice@example.com",
        "username": "alice",
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$fake",
        "roles": ["user"],
        "age_verified": False,
        "age_verified_at": None,
        "risk_score": 0.0,
        "is_active": True,
        "is_banned": False,
        "ban_reason": None,
        "mfa_enabled": False,
        "mfa_secret": None,
        "last_login_at": None,
        "last_login_ip": None,
        "profile": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "deleted_at": None,
    }
    defaults.update(kwargs)
    u = User()
    for k, v in defaults.items():
        setattr(u, k, v)
    return u


def test_create_user():
    u = _make_user(email="bob@example.com", username="bob")
    u.id = uuid.uuid4()
    assert u.id is not None
    assert isinstance(u.id, uuid.UUID)
    assert u.email == "bob@example.com"
    assert u.username == "bob"
    assert u.is_active is True
    assert u.is_banned is False
    assert u.risk_score == 0.0


def test_user_default_roles():
    u = _make_user()
    assert "user" in u.roles


def test_user_multiple_roles():
    u = _make_user(roles=["user", "moderator", "admin"])
    assert set(u.roles) == {"user", "moderator", "admin"}


def test_age_verification_status():
    u = _make_user()
    assert u.age_verified is False
    assert u.age_verified_at is None


def test_age_verified():
    now = datetime.now(timezone.utc)
    u = _make_user(age_verified=True, age_verified_at=now)
    assert u.age_verified is True
    assert u.age_verified_at is not None


def test_risk_score_default():
    u = _make_user()
    assert u.risk_score == 0.0


def test_risk_score_update():
    u = _make_user()
    u.risk_score = 75.5
    assert u.risk_score == 75.5


def test_user_ban_status():
    u = _make_user()
    assert u.is_banned is False
    assert u.ban_reason is None


def test_user_ban():
    u = _make_user()
    u.is_banned = True
    u.ban_reason = "Terms of service violation"
    assert u.is_banned is True
    assert u.ban_reason == "Terms of service violation"


def test_user_mfa_default():
    u = _make_user()
    assert u.mfa_enabled is False
    assert u.mfa_secret is None


def test_user_repr():
    u = _make_user()
    r = repr(u)
    assert "alice" in r


def test_user_soft_delete():
    u = _make_user()
    u.soft_delete()
    assert u.is_deleted is True


def test_user_profile_default():
    u = _make_user()
    assert u.profile is None


def test_user_profile_set():
    u = _make_user()
    u.profile = {"display_name": "Alice", "avatar_url": "https://example.com/a.png"}
    assert u.profile["display_name"] == "Alice"
