"""Factory Boy factories for test objects."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import factory

from src.audit.models import ActionType, ActorType, AuditEvent
from src.core.consent import Consent, ConsentType
from src.core.session import UserSession
from src.core.user import User
from src.moderation.content import Content, ContentStatus, ContentType
from src.moderation.report import Report, ReportStatus


class UserFactory(factory.Factory):
    class Meta:
        model = User

    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    username = factory.Sequence(lambda n: f"user_{n}")
    password_hash = "$argon2id$v=19$m=65536,t=3,p=4$fakehash"
    age_verified = False
    age_verified_at = None
    risk_score = 0.0
    is_active = True
    is_banned = False
    ban_reason = None
    roles = factory.LazyFunction(lambda: ["user"])
    mfa_enabled = False
    mfa_secret = None
    last_login_at = None
    last_login_ip = None
    profile = None


class ContentFactory(factory.Factory):
    class Meta:
        model = Content

    id = factory.LazyFunction(uuid.uuid4)
    submitter_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    content_type = ContentType.TEXT
    raw_content = "Test content"
    metadata = None
    status = ContentStatus.PENDING
    moderation_score = None
    reviewed_at = None
    reviewed_by = None


class AuditEventFactory(factory.Factory):
    class Meta:
        model = AuditEvent

    id = factory.LazyFunction(uuid.uuid4)
    actor_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    actor_type = ActorType.USER
    action = ActionType.CREATE
    resource_type = None
    resource_id = None
    details = None
    ip_address = "127.0.0.1"
    user_agent = "TestAgent/1.0"
    session_id = None
    integrity_hash = None


class ConsentFactory(factory.Factory):
    class Meta:
        model = Consent

    id = factory.LazyFunction(uuid.uuid4)
    user_id = factory.LazyFunction(uuid.uuid4)
    consent_type = ConsentType.CONTENT.value
    granted = True
    granted_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    withdrawn_at = None
    ip_address = "127.0.0.1"
    user_agent = "TestAgent/1.0"
    version = 1


class ReportFactory(factory.Factory):
    class Meta:
        model = Report

    id = factory.LazyFunction(uuid.uuid4)
    reporter_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    target_content_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    target_user_id = None
    reason = "spam"
    description = "This is spam content"
    status = ReportStatus.PENDING
    resolved_at = None
    resolved_by = None


class UserSessionFactory(factory.Factory):
    class Meta:
        model = UserSession

    id = factory.LazyFunction(uuid.uuid4)
    user_id = factory.LazyFunction(uuid.uuid4)
    session_token = factory.LazyFunction(lambda: uuid.uuid4().hex)
    device_fingerprint = None
    ip_address = "127.0.0.1"
    user_agent = "TestAgent/1.0"
    geo_location = None
    is_active = True
    revoked_at = None
    last_active_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
