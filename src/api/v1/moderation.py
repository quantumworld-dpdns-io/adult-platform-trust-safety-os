from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_active_user, get_db_session, require_role
from src.api.exceptions import NotFoundError, ValidationException
from src.api.schemas.moderation import (
    ModerationDecisionRequest,
    ModerationQueueItem,
    ModerationStatsResponse,
)
from src.core.user import User
from src.moderation.content import Content, ContentStatus
from src.moderation.queue import ModerationQueue

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/queue", response_model=list[ModerationQueueItem])
async def get_queue(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_role("admin", "moderator", "reviewer")),
    session: AsyncSession = Depends(get_db_session),
) -> list[ModerationQueueItem]:
    offset = (page - 1) * per_page
    stmt = (
        select(Content)
        .where(Content.status.in_([ContentStatus.PENDING, ContentStatus.IN_REVIEW, ContentStatus.ESCALATED]))
        .order_by(Content.created_at.asc())
        .offset(offset)
        .limit(per_page)
    )
    result = await session.execute(stmt)
    contents = result.scalars().all()

    return [
        ModerationQueueItem(
            id=c.id,
            submitter_id=c.submitter_id,
            content_type=c.content_type.value,
            raw_content=c.raw_content,
            metadata=c.metadata,
            status=c.status.value,
            moderation_score=c.moderation_score,
            created_at=c.created_at,
            reviewed_at=c.reviewed_at,
            reviewed_by=c.reviewed_by,
            priority=(c.metadata or {}).get("queue_priority"),
        )
        for c in contents
    ]


@router.post("/{content_id}/approve")
async def approve_content(
    content_id: uuid.UUID,
    body: ModerationDecisionRequest,
    current_user: User = Depends(require_role("admin", "moderator")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    stmt = select(Content).where(Content.id == content_id)
    result = await session.execute(stmt)
    content = result.scalar_one_or_none()
    if content is None:
        raise NotFoundError("Content not found")

    if content.status not in (ContentStatus.PENDING, ContentStatus.IN_REVIEW, ContentStatus.ESCALATED):
        raise ValidationException(detail=f"Cannot approve content in status {content.status.value}")

    from datetime import datetime, timezone

    content.status = ContentStatus.APPROVED
    content.reviewed_by = str(current_user.id)
    content.reviewed_at = datetime.now(timezone.utc)
    await session.flush()

    logger.info("content_approved", content_id=str(content_id), moderator=str(current_user.id))
    return {"success": True, "content_id": str(content_id), "status": "approved"}


@router.post("/{content_id}/reject")
async def reject_content(
    content_id: uuid.UUID,
    body: ModerationDecisionRequest,
    current_user: User = Depends(require_role("admin", "moderator")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    stmt = select(Content).where(Content.id == content_id)
    result = await session.execute(stmt)
    content = result.scalar_one_or_none()
    if content is None:
        raise NotFoundError("Content not found")

    if content.status not in (ContentStatus.PENDING, ContentStatus.IN_REVIEW, ContentStatus.ESCALATED):
        raise ValidationException(detail=f"Cannot reject content in status {content.status.value}")

    from datetime import datetime, timezone

    content.status = ContentStatus.REJECTED
    content.reviewed_by = str(current_user.id)
    content.reviewed_at = datetime.now(timezone.utc)
    content.metadata = {**(content.metadata or {}), "rejection_reason": body.reason, "rejection_notes": body.notes}
    await session.flush()

    logger.info("content_rejected", content_id=str(content_id), moderator=str(current_user.id), reason=body.reason)
    return {"success": True, "content_id": str(content_id), "status": "rejected"}


@router.post("/{content_id}/escalate")
async def escalate_content(
    content_id: uuid.UUID,
    body: ModerationDecisionRequest,
    current_user: User = Depends(require_role("admin", "moderator", "reviewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    stmt = select(Content).where(Content.id == content_id)
    result = await session.execute(stmt)
    content = result.scalar_one_or_none()
    if content is None:
        raise NotFoundError("Content not found")

    from datetime import datetime, timezone

    content.status = ContentStatus.ESCALATED
    content.metadata = {
        **(content.metadata or {}),
        "escalated_by": str(current_user.id),
        "escalation_reason": body.reason,
        "escalation_notes": body.notes,
        "escalated_at": datetime.now(timezone.utc).isoformat(),
    }
    await session.flush()

    logger.info("content_escalated", content_id=str(content_id), actor=str(current_user.id))
    return {"success": True, "content_id": str(content_id), "status": "escalated"}


@router.get("/stats", response_model=ModerationStatsResponse)
async def moderation_stats(
    current_user: User = Depends(require_role("admin", "moderator")),
    session: AsyncSession = Depends(get_db_session),
) -> ModerationStatsResponse:
    queue = ModerationQueue(session)
    stats = await queue.get_queue_stats()
    return ModerationStatsResponse(**stats)
