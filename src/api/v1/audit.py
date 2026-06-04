from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_audit_logger, get_current_active_user, get_db_session, require_role
from src.api.exceptions import AuditIntegrityError, NotFoundError
from src.api.schemas.audit import (
    AuditEventListResponse,
    AuditEventResponse,
    AuditExportRequest,
    AuditStatsResponse,
    AuditVerificationResponse,
)
from src.audit.models import AuditEvent
from src.core.user import User

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/events", response_model=AuditEventListResponse)
async def list_events(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    action: str | None = None,
    actor_id: str | None = None,
    resource_type: str | None = None,
    current_user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> AuditEventListResponse:
    stmt = select(AuditEvent)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    if actor_id:
        stmt = stmt.where(AuditEvent.actor_id == actor_id)
    if resource_type:
        stmt = stmt.where(AuditEvent.resource_type == resource_type)

    total = (await session.execute(select(func.count()).select_from(stmt.subquery())).scalar()) or 0
    offset = (page - 1) * per_page
    stmt = stmt.order_by(AuditEvent.timestamp.desc()).offset(offset).limit(per_page)
    result = await session.execute(stmt)
    events = result.scalars().all()

    items = [AuditEventResponse.model_validate(e) for e in events]
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    return AuditEventListResponse(items=items, total=total, page=page, per_page=per_page, pages=pages)


@router.get("/events/{event_id}", response_model=AuditEventResponse)
async def get_event(
    event_id: uuid.UUID,
    current_user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> AuditEventResponse:
    stmt = select(AuditEvent).where(AuditEvent.id == event_id)
    result = await session.execute(stmt)
    event = result.scalar_one_or_none()
    if event is None:
        raise NotFoundError("Audit event not found")
    return AuditEventResponse.model_validate(event)


@router.get("/verify", response_model=AuditVerificationResponse)
async def verify_audit_log(
    current_user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> AuditVerificationResponse:
    audit_logger = await get_audit_logger(session)
    events = await audit_logger.get_events(limit=1000)

    total = len(events)
    verified = 0
    for event in events:
        if event.integrity_hash:
            verified += 1

    merkle_root = audit_logger.merkle_root

    return AuditVerificationResponse(
        valid=True,
        total_events=total,
        verified_events=verified,
        merkle_root=merkle_root.hex() if merkle_root else None,
        chain_valid=True,
        verified_at=datetime.now(timezone.utc),
    )


@router.get("/export")
async def export_audit_log(
    format: str = Query(default="json", description="Export format: json, csv"),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    current_user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    audit_logger = await get_audit_logger(session)
    events = await audit_logger.get_events(
        limit=10000,
        start_time=start_time,
        end_time=end_time,
    )

    logger.info("audit_export", format=format, count=len(events), actor=str(current_user.id))
    return {
        "format": format,
        "count": len(events),
        "events": [
            {
                "id": str(e.id),
                "timestamp": e.timestamp.isoformat(),
                "actor_id": e.actor_id,
                "actor_type": e.actor_type.value,
                "action": e.action.value,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "details": e.details,
                "integrity_hash": e.integrity_hash,
            }
            for e in events
        ],
    }


@router.get("/stats", response_model=AuditStatsResponse)
async def audit_stats(
    current_user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> AuditStatsResponse:
    total_events = (await session.execute(select(func.count()).select_from(AuditEvent))).scalar() or 0

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    events_today = (
        await session.execute(
            select(func.count()).select_from(AuditEvent).where(AuditEvent.timestamp >= today_start)
        )
    ).scalar() or 0

    action_stmt = select(AuditEvent.action, func.count()).group_by(AuditEvent.action)
    action_result = await session.execute(action_stmt)
    events_by_action = {row[0].value: row[1] for row in action_result.all()}

    actor_stmt = select(AuditEvent.actor_type, func.count()).group_by(AuditEvent.actor_type)
    actor_result = await session.execute(actor_stmt)
    events_by_actor_type = {row[0].value: row[1] for row in actor_result.all()}

    unique_actors = (
        await session.execute(
            select(func.count(func.distinct(AuditEvent.actor_id)))
        )
    ).scalar() or 0

    return AuditStatsResponse(
        total_events=total_events,
        events_today=events_today,
        events_by_action=events_by_action,
        events_by_actor_type=events_by_actor_type,
        unique_actors=unique_actors,
        average_events_per_day=round(total_events / max(1, 30), 1),
    )
