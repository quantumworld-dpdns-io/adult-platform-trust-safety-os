"""Tests for the Consent model."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from src.core.consent import Consent, ConsentType
from src.core.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _make_consent(db, *, consent_type: str = ConsentType.CONTENT.value, granted: bool = True, version: int = 1):
    c = Consent(
        user_id=uuid.uuid4(),
        consent_type=consent_type,
        granted=granted,
        version=version,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_grant_consent(db):
    c = _make_consent(db)
    assert c.granted is True
    assert c.consent_type == ConsentType.CONTENT.value
    assert c.version == 1
    assert c.is_active is True


def test_withdraw_consent(db):
    c = _make_consent(db)
    assert c.is_active is True
    c.granted = False
    c.withdrawn_at = datetime.now(timezone.utc)
    c.version = 2
    db.commit()
    db.refresh(c)
    assert c.is_active is False
    assert c.withdrawn_at is not None
    assert c.version == 2


def test_consent_types():
    expected = {"content", "data", "third_party", "marketing", "analytics"}
    actual = {ct.value for ct in ConsentType}
    assert actual == expected


def test_consent_versioning(db):
    user_id = uuid.uuid4()
    c1 = Consent(user_id=user_id, consent_type=ConsentType.DATA.value, granted=True, version=1)
    db.add(c1)
    db.commit()

    c1.granted = False
    c1.withdrawn_at = datetime.now(timezone.utc)
    c1.version = 2
    db.commit()
    db.refresh(c1)
    assert c1.version == 2
    assert c1.is_active is False

    c1.granted = True
    c1.withdrawn_at = None
    c1.version = 3
    db.commit()
    db.refresh(c1)
    assert c1.version == 3
    assert c1.is_active is True


def test_consent_repr(db):
    c = _make_consent(db)
    r = repr(c)
    assert "Consent" in r
    assert ConsentType.CONTENT.value in r


def test_consent_ip_address(db):
    c = Consent(
        user_id=uuid.uuid4(),
        consent_type=ConsentType.MARKETING.value,
        granted=True,
        ip_address="192.168.1.100",
        version=1,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    assert c.ip_address == "192.168.1.100"


def test_consent_without_withdrawal_is_active(db):
    c = _make_consent(db)
    assert c.withdrawn_at is None
    assert c.is_active is True
