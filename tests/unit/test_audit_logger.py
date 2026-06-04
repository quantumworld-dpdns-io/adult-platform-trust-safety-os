"""Tests for the AuditLogger with batch logging and integrity hash."""

from __future__ import annotations

import hashlib
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.audit.logger import AuditLogger
from src.audit.models import ActionType, ActorType


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def audit_logger(mock_session):
    with patch("src.audit.logger.settings") as mock_settings:
        mock_settings.audit.batch_size = 10
        logger = AuditLogger(mock_session)
    return logger


async def test_log_event(audit_logger, mock_session):
    event = await audit_logger.log_event(
        actor_id="user-123",
        actor_type=ActorType.USER,
        action=ActionType.LOGIN,
        resource_type="session",
        resource_id="sess-1",
        details={"method": "password"},
        ip_address="10.0.0.1",
        user_agent="Mozilla/5.0",
    )
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()
    assert event.actor_id == "user-123"
    assert event.actor_type == ActorType.USER
    assert event.action == ActionType.LOGIN


async def test_log_event_integrity_hash(audit_logger):
    event = await audit_logger.log_event(
        actor_id="user-456",
        actor_type=ActorType.ADMIN,
        action=ActionType.READ,
    )
    assert event.integrity_hash is not None
    assert len(event.integrity_hash) == 64


async def test_log_event_integrity_hash_is_sha256(audit_logger):
    event = await audit_logger.log_event(
        actor_id="hash-check",
        actor_type=ActorType.USER,
        action=ActionType.CREATE,
    )
    try:
        bytes.fromhex(event.integrity_hash)
        is_hex = True
    except ValueError:
        is_hex = False
    assert is_hex
    assert len(event.integrity_hash) == 64


async def test_batch_logging(audit_logger, mock_session):
    events_data = [
        {"actor_id": "u1", "actor_type": ActorType.USER, "action": ActionType.CREATE},
        {"actor_id": "u2", "actor_type": ActorType.USER, "action": ActionType.READ},
        {"actor_id": "u3", "actor_type": ActorType.USER, "action": ActionType.UPDATE},
    ]
    created = await audit_logger.log_batch(events_data)
    assert len(created) == 3
    assert mock_session.add.call_count >= 3


async def test_merkle_root(audit_logger):
    assert audit_logger.merkle_root is None
    await audit_logger.log_event(
        actor_id="merkle-test",
        actor_type=ActorType.USER,
        action=ActionType.CREATE,
    )
    root = audit_logger.merkle_root
    assert root is not None
    assert isinstance(root, bytes)
    assert len(root) == 32


async def test_flush_batch(audit_logger, mock_session):
    await audit_logger.log_event(
        actor_id="flush-test",
        actor_type=ActorType.USER,
        action=ActionType.CREATE,
    )
    await audit_logger.flush_batch()
    assert len(audit_logger._batch) == 0


async def test_log_event_with_all_fields(audit_logger):
    event = await audit_logger.log_event(
        actor_id="full-test",
        actor_type=ActorType.MODERATOR,
        action=ActionType.MODERATE,
        resource_type="content",
        resource_id="content-789",
        details={"reason": "policy_violation", "severity": "high"},
        ip_address="192.168.1.1",
        user_agent="ModBot/2.0",
        session_id="sess-abc",
    )
    assert event.actor_id == "full-test"
    assert event.actor_type == ActorType.MODERATOR
    assert event.action == ActionType.MODERATE
    assert event.resource_type == "content"
    assert event.details["reason"] == "policy_violation"
