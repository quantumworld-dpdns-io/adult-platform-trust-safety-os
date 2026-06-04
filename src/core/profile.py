from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base, TimestampMixin, UUIDMixin


class UserProfile(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    content_preferences: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=lambda: {
            "mature_content": False,
            "explicit_content": False,
            "content_filters": [],
            "blocked_categories": [],
        },
    )

    safety_settings: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=lambda: {
            "require_consent_for_dm": True,
            "block_minors": True,
            "age_gate_strict": True,
            "content_warning_enabled": True,
            "blocked_users": [],
            "blocked_keywords": [],
            "max_report_threshold": 3,
        },
    )

    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)

    def __repr__(self) -> str:
        return f"<UserProfile user={self.user_id} lang={self.language}>"

    def has_content_preference(self, key: str) -> bool:
        if not self.content_preferences:
            return False
        return self.content_preferences.get(key, False)

    def has_safety_setting(self, key: str) -> bool:
        if not self.safety_settings:
            return False
        return bool(self.safety_settings.get(key))

    def update_content_preferences(self, updates: dict) -> None:
        if self.content_preferences is None:
            self.content_preferences = {}
        self.content_preferences.update(updates)

    def update_safety_settings(self, updates: dict) -> None:
        if self.safety_settings is None:
            self.safety_settings = {}
        self.safety_settings.update(updates)
