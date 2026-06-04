"""Tests for the User ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from src.core.models import Base
from src.core.user import User
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def user(db):
    u = User(
        email="alice@example.com",
        username="alice",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fake",
        roles=["user"],
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def test_create_user(db):
    u = User(
        email="bob@example.com",
        username="bob",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fake",
        roles=["user"],
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    assert u.id is not None
    assert isinstance(u.id, uuid.UUID)
    assert u.email == "bob@example.com"
    assert u.username == "bob"
    assert u.is_active is True
    assert u.is_banned is False
    assert u.risk_score == 0.0


def test_user_default_roles(user):
    assert "user" in user.roles


def test_user_multiple_roles(db):
    u = User(
        email="admin@example.com",
        username="admin",
        password_hash="hash",
        roles=["user", "moderator", "admin"],
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    assert set(u.roles) == {"user", "moderator", "admin"}


def test_age_verification_status(user):
    assert user.age_verified is False
    assert user.age_verified_at is None


def test_age_verified(db):
    now = datetime.now(timezone.utc)
    u = User(
        email="verified@example.com",
        username="verified",
        password_hash="hash",
        age_verified=True,
        age_verified_at=now,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    assert u.age_verified is True
    assert u.age_verified_at is not None


def test_risk_score_default(user):
    assert user.risk_score == 0.0


def test_risk_score_update(user, db):
    user.risk_score = 75.5
    db.commit()
    db.refresh(user)
    assert user.risk_score == 75.5


def test_user_ban_status(user):
    assert user.is_banned is False
    assert user.ban_reason is None


def test_user_ban(user, db):
    user.is_banned = True
    user.ban_reason = "Terms of service violation"
    db.commit()
    db.refresh(user)
    assert user.is_banned is True
    assert user.ban_reason == "Terms of service violation"


def test_user_mfa_default(user):
    assert user.mfa_enabled is False
    assert user.mfa_secret is None


def test_user_repr(user):
    r = repr(user)
    assert "alice" in r


def test_user_soft_delete(user, db):
    user.soft_delete()
    db.commit()
    db.refresh(user)
    assert user.is_deleted is True


def test_user_profile_default(user):
    assert user.profile is None


def test_user_profile_set(user, db):
    user.profile = {"display_name": "Alice", "avatar_url": "https://example.com/a.png"}
    db.commit()
    db.refresh(user)
    assert user.profile["display_name"] == "Alice"
