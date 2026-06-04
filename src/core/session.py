from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .models import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class UserSession(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "user_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    session_token: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    device_fingerprint: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    geo_location: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
    )

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Session user={self.user_id} ip={self.ip_address} "
            f"active={self.is_active}>"
        )

    @property
    def is_expired(self) -> bool:
        if self.last_active_at is None:
            return True
        from datetime import timedelta
        return (datetime.now(timezone.utc) - self.last_active_at) > timedelta(hours=24)

    def revoke(self) -> None:
        self.is_active = False
        self.revoked_at = datetime.now(timezone.utc)

    def touch(self) -> None:
        self.last_active_at = datetime.now(timezone.utc)
