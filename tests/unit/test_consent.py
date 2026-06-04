"""Tests for the Consent model."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from src.core.consent import Consent, ConsentType


def _make_consent(**kwargs):
    defaults = {
        "user_id": uuid.uuid4(),
        "consent_type": ConsentType.CONTENT.value,
        "granted": True,
        "version": 1,
    }
    defaults.update(kwargs)
    c = Consent()
    for k, v in defaults.items():
        setattr(c, k, v)
    return c


def test_grant_consent():
    c = _make_consent()
    assert c.granted is True
    assert c.consent_type == ConsentType.CONTENT.value
    assert c.version == 1
    assert c.is_active is True


def test_withdraw_consent():
    c = _make_consent()
    assert c.is_active is True
    c.granted = False
    c.withdrawn_at = datetime.now(timezone.utc)
    c.version = 2
    assert c.is_active is False
    assert c.withdrawn_at is not None
    assert c.version == 2


def test_consent_types():
    expected = {"content", "data", "third_party", "marketing", "analytics"}
    actual = {ct.value for ct in ConsentType}
    assert actual == expected


def test_consent_versioning():
    user_id = uuid.uuid4()
    c = _make_consent(user_id=user_id, consent_type=ConsentType.DATA.value)
    assert c.version == 1
    c.granted = False
    c.withdrawn_at = datetime.now(timezone.utc)
    c.version = 2
    assert c.is_active is False
    c.granted = True
    c.withdrawn_at = None
    c.version = 3
    assert c.is_active is True
    assert c.version == 3


def test_consent_repr():
    c = _make_consent()
    r = repr(c)
    assert "Consent" in r
    assert ConsentType.CONTENT.value in r


def test_consent_ip_address():
    c = _make_consent(ip_address="192.168.1.100", consent_type=ConsentType.MARKETING.value)
    assert c.ip_address == "192.168.1.100"


def test_consent_without_withdrawal_is_active():
    c = _make_consent()
    assert c.withdrawn_at is None
    assert c.is_active is True


def test_consent_is_active_granted_false():
    c = _make_consent(granted=False)
    assert c.is_active is False
