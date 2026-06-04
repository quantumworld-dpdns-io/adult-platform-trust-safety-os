from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from .models import Base, UUIDMixin


class ConsentType(str, Enum):
    CONTENT = "content"
    DATA = "data"
    THIRD_PARTY = "third_party"
    MARKETING = "marketing"
    ANALYTICS = "analytics"


class Consent(Base, UUIDMixin):
    __tablename__ = "consents"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    consent_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(default=1, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<Consent user={self.user_id} type={self.consent_type} "
            f"granted={self.granted} v{self.version}>"
        )

    @property
    def is_active(self) -> bool:
        return self.granted and self.withdrawn_at is None


from typing import TYPE_CHECKING, Mapped as _Mapped  # noqa: E402  (avoid circular at module level)

if TYPE_CHECKING:
    pass
