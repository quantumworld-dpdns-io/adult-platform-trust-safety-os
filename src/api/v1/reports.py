from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_active_user, get_db_session
from src.api.exceptions import NotFoundError
from src.api.schemas.moderation import ReportCreate, ReportResponse
from src.core.user import User
from src.moderation.report import Report, ReportStatus

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("", response_model=ReportResponse, status_code=201)
async def create_report(
    body: ReportCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> ReportResponse:
    report = Report(
        reporter_id=str(current_user.id),
        target_content_id=str(body.target_content_id) if body.target_content_id else None,
        target_user_id=str(body.target_user_id) if body.target_user_id else None,
        reason=body.reason,
        description=body.description,
        status=ReportStatus.PENDING,
    )
    session.add(report)
    await session.flush()

    logger.info("report_created", report_id=str(report.id), reporter=str(current_user.id))
    return ReportResponse.model_validate(report)


@router.get("")
async def list_reports(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status: str | None = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    stmt = select(Report)
    if status:
        stmt = stmt.where(Report.status == ReportStatus(status))

    total = (await session.execute(select(func.count()).select_from(stmt.subquery())).scalar()) or 0
    offset = (page - 1) * per_page
    stmt = stmt.order_by(Report.created_at.desc()).offset(offset).limit(per_page)
    result = await session.execute(stmt)
    reports = result.scalars().all()

    items = [ReportResponse.model_validate(r) for r in reports]
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    return {"items": [i.model_dump() for i in items], "total": total, "page": page, "per_page": per_page, "pages": pages}


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> ReportResponse:
    stmt = select(Report).where(Report.id == report_id)
    result = await session.execute(stmt)
    report = result.scalar_one_or_none()
    if report is None:
        raise NotFoundError("Report not found")
    return ReportResponse.model_validate(report)


@router.put("/{report_id}/resolve")
async def resolve_report(
    report_id: uuid.UUID,
    resolution: str = Query(description="Resolution: resolved or dismissed"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    stmt = select(Report).where(Report.id == report_id)
    result = await session.execute(stmt)
    report = result.scalar_one_or_none()
    if report is None:
        raise NotFoundError("Report not found")

    from datetime import datetime, timezone

    if resolution == "resolved":
        report.status = ReportStatus.RESOLVED
    elif resolution == "dismissed":
        report.status = ReportStatus.DISMISSED
    else:
        from src.api.exceptions import ValidationException
        raise ValidationException(detail="Resolution must be 'resolved' or 'dismissed'")

    report.resolved_by = str(current_user.id)
    report.resolved_at = datetime.now(timezone.utc)
    await session.flush()

    logger.info("report_resolved", report_id=str(report_id), resolution=resolution, actor=str(current_user.id))
    return {"success": True, "report_id": str(report_id), "status": resolution}
