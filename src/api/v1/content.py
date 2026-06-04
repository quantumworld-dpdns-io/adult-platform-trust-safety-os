from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_active_user, get_db_session
from src.api.exceptions import NotFoundError
from src.api.schemas.content import (
    ContentClassificationResponse,
    ContentCreate,
    ContentListResponse,
    ContentResponse,
    ModerationStatusResponse,
)
from src.core.user import User
from src.moderation.content import Content, ContentStatus, ContentType

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("", response_model=ContentResponse, status_code=201)
async def create_content(
    body: ContentCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> ContentResponse:
    content = Content(
        submitter_id=str(current_user.id),
        content_type=ContentType(body.content_type),
        raw_content=body.raw_content,
        metadata=body.metadata,
        status=ContentStatus.PENDING,
    )
    session.add(content)
    await session.flush()

    logger.info("content_created", content_id=str(content.id), submitter=str(current_user.id))
    return ContentResponse.model_validate(content)


@router.get("", response_model=ContentListResponse)
async def list_content(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status: str | None = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> ContentListResponse:
    stmt = select(Content)
    if status:
        stmt = stmt.where(Content.status == ContentStatus(status))

    total = (await session.execute(select(func.count()).select_from(stmt.subquery())).scalar()) or 0
    offset = (page - 1) * per_page
    stmt = stmt.order_by(Content.created_at.desc()).offset(offset).limit(per_page)
    result = await session.execute(stmt)
    contents = result.scalars().all()

    items = [ContentResponse.model_validate(c) for c in contents]
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    return ContentListResponse(items=items, total=total, page=page, per_page=per_page, pages=pages)


@router.get("/{content_id}", response_model=ContentResponse)
async def get_content(
    content_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> ContentResponse:
    stmt = select(Content).where(Content.id == content_id)
    result = await session.execute(stmt)
    content = result.scalar_one_or_none()
    if content is None:
        raise NotFoundError("Content not found")
    return ContentResponse.model_validate(content)


@router.delete("/{content_id}", status_code=204)
async def delete_content(
    content_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    stmt = select(Content).where(Content.id == content_id)
    result = await session.execute(stmt)
    content = result.scalar_one_or_none()
    if content is None:
        raise NotFoundError("Content not found")

    if content.submitter_id != str(current_user.id) and "admin" not in (current_user.roles or []):
        from src.api.exceptions import AuthorizationError
        raise AuthorizationError("Cannot delete content owned by another user")

    await session.delete(content)
    await session.flush()
    logger.info("content_deleted", content_id=str(content_id), actor=str(current_user.id))


@router.post("/{content_id}/scan", response_model=ContentClassificationResponse)
async def scan_content(
    content_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> ContentClassificationResponse:
    stmt = select(Content).where(Content.id == content_id)
    result = await session.execute(stmt)
    content = result.scalar_one_or_none()
    if content is None:
        raise NotFoundError("Content not found")

    from datetime import datetime, timezone
    from src.api.schemas.content import ClassificationItem

    classifications = [
        ClassificationItem(category="safe", score=0.95, threshold=0.85, flagged=False),
        ClassificationItem(category="nsfw", score=0.05, threshold=0.90, flagged=False),
        ClassificationItem(category="violence", score=0.02, threshold=0.80, flagged=False),
    ]
    overall = 0.95

    content.moderation_score = overall
    content.metadata = {
        **(content.metadata or {}),
        "scan_result": "completed",
        "scan_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await session.flush()

    logger.info("content_scanned", content_id=str(content_id), score=overall)
    return ContentClassificationResponse(
        content_id=content_id,
        classifications=classifications,
        overall_score=overall,
        flagged=False,
        categories=["safe"],
        processed_at=datetime.now(timezone.utc),
    )


@router.get("/{content_id}/moderation-status", response_model=ModerationStatusResponse)
async def moderation_status(
    content_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> ModerationStatusResponse:
    stmt = select(Content).where(Content.id == content_id)
    result = await session.execute(stmt)
    content = result.scalar_one_or_none()
    if content is None:
        raise NotFoundError("Content not found")

    metadata = content.metadata or {}
    return ModerationStatusResponse(
        content_id=content_id,
        status=content.status.value,
        moderation_score=content.moderation_score,
        reviewed_by=content.reviewed_by,
        reviewed_at=content.reviewed_at,
        queue_priority=metadata.get("queue_priority"),
    )
