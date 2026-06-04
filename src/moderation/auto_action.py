"""Automated enforcement actions with audit logging."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit.logger import AuditLogger
from src.audit.models import ActionType, ActorType

logger = structlog.get_logger(__name__)


class AutoEnforcement:
    """Execute automated moderation enforcement actions.

    Every action is recorded in the audit log for traceability.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._audit = AuditLogger(session)

    async def warn_user(
        self,
        *,
        user_id: str,
        reason: str,
        moderator_id: str = "system",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Issue a formal warning to a user."""
        warn_details = {
            "action": "warn",
            "reason": reason,
            "issued_at": datetime.now(timezone.utc).isoformat(),
            **(details or {}),
        }

        await self._audit.log_event(
            actor_id=moderator_id,
            actor_type=ActorType.SYSTEM if moderator_id == "system" else ActorType.MODERATOR,
            action=ActionType.MODERATE,
            resource_type="user",
            resource_id=user_id,
            details=warn_details,
        )

        logger.info("user_warned", user_id=user_id, reason=reason)
        return {"success": True, "action": "warn", "user_id": user_id, "reason": reason}

    async def restrict_user(
        self,
        *,
        user_id: str,
        reason: str,
        restrictions: list[str],
        duration_hours: int = 24,
        moderator_id: str = "system",
    ) -> dict[str, Any]:
        """Apply temporary restrictions to a user account."""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=duration_hours)

        details = {
            "action": "restrict",
            "reason": reason,
            "restrictions": restrictions,
            "duration_hours": duration_hours,
            "expires_at": expires_at.isoformat(),
            "issued_at": datetime.now(timezone.utc).isoformat(),
        }

        await self._audit.log_event(
            actor_id=moderator_id,
            actor_type=ActorType.SYSTEM if moderator_id == "system" else ActorType.MODERATOR,
            action=ActionType.MODERATE,
            resource_type="user",
            resource_id=user_id,
            details=details,
        )

        logger.info(
            "user_restricted",
            user_id=user_id,
            restrictions=restrictions,
            duration_hours=duration_hours,
        )
        return {
            "success": True,
            "action": "restrict",
            "user_id": user_id,
            "restrictions": restrictions,
            "expires_at": expires_at.isoformat(),
        }

    async def suspend_user(
        self,
        *,
        user_id: str,
        reason: str,
        duration_days: int = 7,
        moderator_id: str = "system",
    ) -> dict[str, Any]:
        """Suspend a user account for a fixed period."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=duration_days)

        details = {
            "action": "suspend",
            "reason": reason,
            "duration_days": duration_days,
            "expires_at": expires_at.isoformat(),
            "issued_at": datetime.now(timezone.utc).isoformat(),
        }

        await self._audit.log_event(
            actor_id=moderator_id,
            actor_type=ActorType.SYSTEM if moderator_id == "system" else ActorType.MODERATOR,
            action=ActionType.MODERATE,
            resource_type="user",
            resource_id=user_id,
            details=details,
        )

        logger.info("user_suspended", user_id=user_id, duration_days=duration_days, reason=reason)
        return {
            "success": True,
            "action": "suspend",
            "user_id": user_id,
            "duration_days": duration_days,
            "expires_at": expires_at.isoformat(),
        }

    async def ban_user(
        self,
        *,
        user_id: str,
        reason: str,
        moderator_id: str = "system",
        permanent: bool = True,
    ) -> dict[str, Any]:
        """Permanently or temporarily ban a user."""
        details = {
            "action": "ban",
            "reason": reason,
            "permanent": permanent,
            "issued_at": datetime.now(timezone.utc).isoformat(),
        }

        await self._audit.log_event(
            actor_id=moderator_id,
            actor_type=ActorType.SYSTEM if moderator_id == "system" else ActorType.MODERATOR,
            action=ActionType.BAN,
            resource_type="user",
            resource_id=user_id,
            details=details,
        )

        logger.info("user_banned", user_id=user_id, permanent=permanent, reason=reason)
        return {
            "success": True,
            "action": "ban",
            "user_id": user_id,
            "permanent": permanent,
            "reason": reason,
        }

    async def remove_content(
        self,
        *,
        content_id: uuid.UUID,
        reason: str,
        moderator_id: str = "system",
    ) -> dict[str, Any]:
        """Remove content that violates platform policies."""
        details = {
            "action": "remove_content",
            "reason": reason,
            "removed_at": datetime.now(timezone.utc).isoformat(),
        }

        await self._audit.log_event(
            actor_id=moderator_id,
            actor_type=ActorType.SYSTEM if moderator_id == "system" else ActorType.MODERATOR,
            action=ActionType.DELETE,
            resource_type="content",
            resource_id=str(content_id),
            details=details,
        )

        logger.info("content_removed", content_id=str(content_id), reason=reason)
        return {
            "success": True,
            "action": "remove_content",
            "content_id": str(content_id),
            "reason": reason,
        }

    async def apply_timeout(
        self,
        *,
        user_id: str,
        reason: str,
        duration_minutes: int = 30,
        moderator_id: str = "system",
    ) -> dict[str, Any]:
        """Apply a temporary timeout preventing user from posting."""
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)

        details = {
            "action": "timeout",
            "reason": reason,
            "duration_minutes": duration_minutes,
            "expires_at": expires_at.isoformat(),
            "issued_at": datetime.now(timezone.utc).isoformat(),
        }

        await self._audit.log_event(
            actor_id=moderator_id,
            actor_type=ActorType.SYSTEM if moderator_id == "system" else ActorType.MODERATOR,
            action=ActionType.MODERATE,
            resource_type="user",
            resource_id=user_id,
            details=details,
        )

        logger.info(
            "user_timeout_applied",
            user_id=user_id,
            duration_minutes=duration_minutes,
            reason=reason,
        )
        return {
            "success": True,
            "action": "timeout",
            "user_id": user_id,
            "duration_minutes": duration_minutes,
            "expires_at": expires_at.isoformat(),
        }
