"""Audit event ORM model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.models import Base


class ActorType(str, enum.Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    MODERATOR = "MODERATOR"
    ADMIN = "ADMIN"


class ActionType(str, enum.Enum):
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    EXPORT = "EXPORT"
    VERIFY = "VERIFY"
    MODERATE = "MODERATE"
    BAN = "BAN"


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_actor_id", "actor_id"),
        Index("ix_audit_events_resource", "resource_type", "resource_id"),
        Index("ix_audit_events_timestamp", "timestamp"),
        Index("ix_audit_events_action", "action"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    actor_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_type: Mapped[ActorType] = mapped_column(
        Enum(ActorType, name="actor_type_enum"), nullable=False
    )
    action: Mapped[ActionType] = mapped_column(
        Enum(ActionType, name="action_type_enum"), nullable=False
    )
    resource_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    integrity_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
