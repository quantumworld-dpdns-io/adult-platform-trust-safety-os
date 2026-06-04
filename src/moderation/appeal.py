"""Appeal service for moderation decisions."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit.logger import AuditLogger
from src.audit.models import ActionType, ActorType
from src.moderation.content import Content, ContentStatus

logger = structlog.get_logger(__name__)


class AppealStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"


class AppealService:
    """Handle user appeals against moderation decisions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._audit = AuditLogger(session)

    async def submit_appeal(
        self,
        *,
        content_id: uuid.UUID,
        user_id: str,
        reason: str,
        additional_context: str | None = None,
    ) -> dict[str, Any]:
        """Submit an appeal for a moderation decision."""
        stmt = select(Content).where(Content.id == content_id)
        result = await self._session.execute(stmt)
        content = result.scalar_one_or_none()

        if content is None:
            return {"success": False, "error": "content_not_found"}

        if content.status not in (ContentStatus.REJECTED, ContentStatus.ESCALATED):
            return {"success": False, "error": "only rejected or escalated content can be appealed"}

        if content.submitter_id != user_id:
            return {"success": False, "error": "only the content submitter can appeal"}

        metadata = content.metadata or {}
        appeals = metadata.get("appeals", [])
        appeal_id = str(uuid.uuid4())
        appeals.append({
            "appeal_id": appeal_id,
            "status": AppealStatus.PENDING.value,
            "reason": reason,
            "additional_context": additional_context,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
        })
        metadata["appeals"] = appeals
        content.metadata = metadata
        content.status = ContentStatus.ESCALATED
        await self._session.flush()

        await self._audit.log_event(
            actor_id=user_id,
            actor_type=ActorType.USER,
            action=ActionType.CREATE,
            resource_type="appeal",
            resource_id=appeal_id,
            details={"content_id": str(content_id), "reason": reason},
        )

        logger.info("appeal_submitted", content_id=str(content_id), appeal_id=appeal_id)
        return {"success": True, "appeal_id": appeal_id, "content_id": str(content_id)}

    async def review_appeal(
        self,
        *,
        content_id: uuid.UUID,
        appeal_id: str,
        reviewer_id: str,
    ) -> dict[str, Any]:
        """Mark an appeal as under review."""
        stmt = select(Content).where(Content.id == content_id)
        result = await self._session.execute(stmt)
        content = result.scalar_one_or_none()

        if content is None:
            return {"success": False, "error": "content_not_found"}

        metadata = content.metadata or {}
        appeals = metadata.get("appeals", [])
        appeal = next((a for a in appeals if a["appeal_id"] == appeal_id), None)

        if appeal is None:
            return {"success": False, "error": "appeal_not_found"}

        appeal["status"] = AppealStatus.PENDING.value
        appeal["reviewer_id"] = reviewer_id
        appeal["reviewed_at"] = datetime.now(timezone.utc).isoformat()
        metadata["appeals"] = appeals
        content.metadata = metadata
        await self._session.flush()

        await self._audit.log_event(
            actor_id=reviewer_id,
            actor_type=ActorType.MODERATOR,
            action=ActionType.READ,
            resource_type="appeal",
            resource_id=appeal_id,
            details={"content_id": str(content_id), "action": "review_started"},
        )

        return {"success": True, "appeal_id": appeal_id}

    async def approve_appeal(
        self,
        *,
        content_id: uuid.UUID,
        appeal_id: str,
        reviewer_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Approve an appeal and restore the content."""
        stmt = select(Content).where(Content.id == content_id)
        result = await self._session.execute(stmt)
        content = result.scalar_one_or_none()

        if content is None:
            return {"success": False, "error": "content_not_found"}

        metadata = content.metadata or {}
        appeals = metadata.get("appeals", [])
        appeal = next((a for a in appeals if a["appeal_id"] == appeal_id), None)

        if appeal is None:
            return {"success": False, "error": "appeal_not_found"}

        appeal["status"] = AppealStatus.APPROVED.value
        appeal["decision_reason"] = reason
        appeal["decided_at"] = datetime.now(timezone.utc).isoformat()
        metadata["appeals"] = appeals
        content.metadata = metadata
        content.status = ContentStatus.APPROVED
        content.reviewed_by = reviewer_id
        content.reviewed_at = datetime.now(timezone.utc)
        await self._session.flush()

        await self._audit.log_event(
            actor_id=reviewer_id,
            actor_type=ActorType.MODERATOR,
            action=ActionType.MODERATE,
            resource_type="appeal",
            resource_id=appeal_id,
            details={
                "content_id": str(content_id),
                "decision": "approved",
                "reason": reason,
            },
        )

        logger.info("appeal_approved", content_id=str(content_id), appeal_id=appeal_id)
        return {"success": True, "appeal_id": appeal_id, "content_status": "APPROVED"}

    async def reject_appeal(
        self,
        *,
        content_id: uuid.UUID,
        appeal_id: str,
        reviewer_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Reject an appeal, keeping the moderation decision."""
        stmt = select(Content).where(Content.id == content_id)
        result = await self._session.execute(stmt)
        content = result.scalar_one_or_none()

        if content is None:
            return {"success": False, "error": "content_not_found"}

        metadata = content.metadata or {}
        appeals = metadata.get("appeals", [])
        appeal = next((a for a in appeals if a["appeal_id"] == appeal_id), None)

        if appeal is None:
            return {"success": False, "error": "appeal_not_found"}

        appeal["status"] = AppealStatus.REJECTED.value
        appeal["decision_reason"] = reason
        appeal["decided_at"] = datetime.now(timezone.utc).isoformat()
        metadata["appeals"] = appeals
        content.metadata = metadata
        await self._session.flush()

        await self._audit.log_event(
            actor_id=reviewer_id,
            actor_type=ActorType.MODERATOR,
            action=ActionType.MODERATE,
            resource_type="appeal",
            resource_id=appeal_id,
            details={
                "content_id": str(content_id),
                "decision": "rejected",
                "reason": reason,
            },
        )

        logger.info("appeal_rejected", content_id=str(content_id), appeal_id=appeal_id)
        return {"success": True, "appeal_id": appeal_id, "content_status": content.status.value}

    async def escalate_appeal(
        self,
        *,
        content_id: uuid.UUID,
        appeal_id: str,
        reviewer_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Escalate an appeal to a senior moderator or admin."""
        stmt = select(Content).where(Content.id == content_id)
        result = await self._session.execute(stmt)
        content = result.scalar_one_or_none()

        if content is None:
            return {"success": False, "error": "content_not_found"}

        metadata = content.metadata or {}
        appeals = metadata.get("appeals", [])
        appeal = next((a for a in appeals if a["appeal_id"] == appeal_id), None)

        if appeal is None:
            return {"success": False, "error": "appeal_not_found"}

        appeal["status"] = AppealStatus.ESCALATED.value
        appeal["escalation_reason"] = reason
        appeal["escalated_at"] = datetime.now(timezone.utc).isoformat()
        appeal["escalated_by"] = reviewer_id
        metadata["appeals"] = appeals
        content.metadata = metadata
        content.status = ContentStatus.ESCALATED
        await self._session.flush()

        await self._audit.log_event(
            actor_id=reviewer_id,
            actor_type=ActorType.MODERATOR,
            action=ActionType.MODERATE,
            resource_type="appeal",
            resource_id=appeal_id,
            details={
                "content_id": str(content_id),
                "action": "escalated",
                "reason": reason,
            },
        )

        logger.info("appeal_escalated", content_id=str(content_id), appeal_id=appeal_id)
        return {"success": True, "appeal_id": appeal_id, "content_status": "ESCALATED"}
