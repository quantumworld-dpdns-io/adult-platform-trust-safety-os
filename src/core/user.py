from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)

    age_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    age_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    risk_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ban_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    roles: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=["user"], server_default='{"user"}', nullable=False
    )

    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(32), nullable=True)

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)

    profile: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)

    def __repr__(self) -> str:
        return f"<User {self.username!r} email={self.email!r}>"
