"""Moderation queue management with prioritization and SLA tracking."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.moderation.content import Content, ContentStatus

logger = structlog.get_logger(__name__)

SLA_HOURS: dict[ContentStatus, int] = {
    ContentStatus.PENDING: 24,
    ContentStatus.IN_REVIEW: 48,
}


class ModerationQueue:
    """FIFO queue with priority support, reassignment, and SLA tracking."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_to_queue(
        self,
        content_id: uuid.UUID,
        *,
        priority: int = 0,
    ) -> dict[str, Any]:
        """Place content into the moderation queue."""
        stmt = select(Content).where(Content.id == content_id)
        result = await self._session.execute(stmt)
        content = result.scalar_one_or_none()

        if content is None:
            return {"success": False, "error": "content_not_found"}

        if content.status not in (ContentStatus.PENDING, ContentStatus.ESCALATED):
            return {"success": False, "error": f"content already in status {content.status.value}"}

        content.status = ContentStatus.PENDING
        content.metadata = {
            **(content.metadata or {}),
            "queue_priority": priority,
            "queued_at": datetime.now(timezone.utc).isoformat(),
        }
        await self._session.flush()

        logger.info("content_added_to_queue", content_id=str(content_id), priority=priority)
        return {"success": True, "content_id": str(content_id), "priority": priority}

    async def get_next(self, reviewer_id: str | None = None) -> Content | None:
        """Get the next highest-priority item from the queue."""
        stmt = (
            select(Content)
            .where(Content.status == ContentStatus.PENDING)
            .order_by(
                Content.metadata["queue_priority"].as_float().desc(),  # type: ignore[union-attr]
                Content.created_at.asc(),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        content = result.scalar_one_or_none()

        if content is None:
            return None

        content.status = ContentStatus.IN_REVIEW
        content.reviewed_by = reviewer_id
        content.reviewed_at = datetime.now(timezone.utc)
        await self._session.flush()

        logger.info(
            "content_dispatched",
            content_id=str(content.id),
            reviewer_id=reviewer_id,
        )
        return content

    async def get_queue_stats(self) -> dict[str, Any]:
        """Return aggregate queue statistics."""
        pending_stmt = (
            select(func.count())
            .select_from(Content)
            .where(Content.status == ContentStatus.PENDING)
        )
        pending = (await self._session.execute(pending_stmt)).scalar() or 0

        in_review_stmt = (
            select(func.count())
            .select_from(Content)
            .where(Content.status == ContentStatus.IN_REVIEW)
        )
        in_review = (await self._session.execute(in_review_stmt)).scalar() or 0

        escalated_stmt = (
            select(func.count())
            .select_from(Content)
            .where(Content.status == ContentStatus.ESCALATED)
        )
        escalated = (await self._session.execute(escalated_stmt)).scalar() or 0

        approved_stmt = (
            select(func.count())
            .select_from(Content)
            .where(Content.status == ContentStatus.APPROVED)
        )
        approved = (await self._session.execute(approved_stmt)).scalar() or 0

        rejected_stmt = (
            select(func.count())
            .select_from(Content)
            .where(Content.status == ContentStatus.REJECTED)
        )
        rejected = (await self._session.execute(rejected_stmt)).scalar() or 0

        overdue = await self.get_overdue_items()

        return {
            "pending": pending,
            "in_review": in_review,
            "escalated": escalated,
            "approved": approved,
            "rejected": rejected,
            "total_active": pending + in_review + escalated,
            "overdue_count": len(overdue),
        }

    async def prioritize(
        self,
        content_id: uuid.UUID,
        priority: int,
    ) -> dict[str, Any]:
        """Update the priority of a queued item."""
        stmt = select(Content).where(Content.id == content_id)
        result = await self._session.execute(stmt)
        content = result.scalar_one_or_none()

        if content is None:
            return {"success": False, "error": "content_not_found"}

        metadata = content.metadata or {}
        metadata["queue_priority"] = priority
        content.metadata = metadata
        await self._session.flush()

        return {"success": True, "content_id": str(content_id), "priority": priority}

    async def reassign(
        self,
        content_id: uuid.UUID,
        new_reviewer_id: str,
    ) -> dict[str, Any]:
        """Reassign a content item to a different moderator."""
        stmt = select(Content).where(Content.id == content_id)
        result = await self._session.execute(stmt)
        content = result.scalar_one_or_none()

        if content is None:
            return {"success": False, "error": "content_not_found"}

        old_reviewer = content.reviewed_by
        content.reviewed_by = new_reviewer_id
        await self._session.flush()

        logger.info(
            "content_reassigned",
            content_id=str(content_id),
            old_reviewer=old_reviewer,
            new_reviewer=new_reviewer_id,
        )
        return {
            "success": True,
            "content_id": str(content_id),
            "old_reviewer": old_reviewer,
            "new_reviewer": new_reviewer_id,
        }

    async def get_overdue_items(self) -> list[dict[str, Any]]:
        """Return items that have exceeded their SLA time."""
        now = datetime.now(timezone.utc)
        overdue: list[dict[str, Any]] = []

        for status, hours in SLA_HOURS.items():
            cutoff = now - timedelta(hours=hours)
            stmt = (
                select(Content)
                .where(Content.status == status)
                .where(Content.created_at < cutoff)
            )
            result = await self._session.execute(stmt)
            for content in result.scalars().all():
                age_hours = (now - content.created_at).total_seconds() / 3600 if content.created_at else 0
                overdue.append({
                    "content_id": str(content.id),
                    "status": content.status.value,
                    "created_at": content.created_at.isoformat() if content.created_at else None,
                    "age_hours": round(age_hours, 1),
                    "sla_hours": hours,
                    "overdue_by_hours": round(age_hours - hours, 1),
                    "reviewed_by": content.reviewed_by,
                })

        overdue.sort(key=lambda x: x["overdue_by_hours"], reverse=True)
        return overdue
