"""Factory Boy factories for test objects."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import factory


class UserFactory(factory.Factory):
    class Meta:
        lazy_import = True
        model = "src.core.user:User"

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


class AuditEventFactory(factory.Factory):
    class Meta:
        lazy_import = True
        model = "src.audit.models:AuditEvent"

    id = factory.LazyFunction(uuid.uuid4)
    actor_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    actor_type = factory.LazyFunction(lambda: __import__("src.audit.models", fromlist=["ActorType"]).ActorType.USER)
    action = factory.LazyFunction(lambda: __import__("src.audit.models", fromlist=["ActionType"]).ActionType.CREATE)
    resource_type = None
    resource_id = None
    details = None
    ip_address = "127.0.0.1"
    user_agent = "TestAgent/1.0"
    session_id = None
    integrity_hash = None


class ContentFactory(factory.Factory):
    class Meta:
        lazy_import = True
        model = "src.moderation.content:Content"

    submitter_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    content_type = factory.LazyFunction(lambda: __import__("src.moderation.content", fromlist=["ContentType"]).ContentType.TEXT)
    raw_content = "Test content"
    status = factory.LazyFunction(lambda: __import__("src.moderation.content", fromlist=["ContentStatus"]).ContentStatus.PENDING)
    moderation_score = None
    reviewed_at = None
    reviewed_by = None


class ConsentFactory(factory.Factory):
    class Meta:
        lazy_import = True
        model = "src.core.consent:Consent"

    id = factory.LazyFunction(uuid.uuid4)
    user_id = factory.LazyFunction(uuid.uuid4)
    consent_type = "content"
    granted = True
    granted_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    withdrawn_at = None
    ip_address = "127.0.0.1"
    user_agent = "TestAgent/1.0"
    version = 1


class ReportFactory(factory.Factory):
    class Meta:
        lazy_import = True
        model = "src.moderation.report:Report"

    id = factory.LazyFunction(uuid.uuid4)
    reporter_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    target_content_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    target_user_id = None
    reason = "spam"
    description = "This is spam content"
    status = factory.LazyFunction(lambda: __import__("src.moderation.report", fromlist=["ReportStatus"]).ReportStatus.PENDING)
    resolved_at = None
    resolved_by = None


class UserSessionFactory(factory.Factory):
    class Meta:
        lazy_import = True
        model = "src.core.session:UserSession"

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
