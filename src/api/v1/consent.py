from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_active_user, get_db_session
from src.api.exceptions import NotFoundError
from src.api.schemas.common import PaginatedResponse
from src.api.schemas.user import UserResponse
from src.core.consent import Consent, ConsentType
from src.core.user import User

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("")
async def list_consents(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    total = (
        await session.execute(
            select(func.count()).select_from(Consent).where(Consent.user_id == current_user.id)
        )
    ).scalar() or 0
    offset = (page - 1) * per_page
    stmt = (
        select(Consent)
        .where(Consent.user_id == current_user.id)
        .order_by(Consent.granted_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await session.execute(stmt)
    consents = result.scalars().all()

    items = [
        {
            "id": str(c.id),
            "user_id": str(c.user_id),
            "consent_type": c.consent_type,
            "granted": c.granted,
            "granted_at": c.granted_at.isoformat(),
            "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None,
            "version": c.version,
            "is_active": c.is_active,
        }
        for c in consents
    ]
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    return {"items": items, "total": total, "page": page, "per_page": per_page, "pages": pages}


@router.post("", status_code=201)
async def create_consent(
    consent_type: str,
    granted: bool,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    consent = Consent(
        user_id=current_user.id,
        consent_type=consent_type,
        granted=granted,
        ip_address=client_ip,
        user_agent=user_agent,
        version=1,
    )
    session.add(consent)
    await session.flush()

    logger.info("consent_created", user_id=str(current_user.id), consent_type=consent_type, granted=granted)
    return {
        "id": str(consent.id),
        "consent_type": consent.consent_type,
        "granted": consent.granted,
        "granted_at": consent.granted_at.isoformat(),
        "version": consent.version,
    }


@router.put("/{consent_id}")
async def update_consent(
    consent_id: uuid.UUID,
    granted: bool,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    stmt = select(Consent).where(Consent.id == consent_id, Consent.user_id == current_user.id)
    result = await session.execute(stmt)
    consent = result.scalar_one_or_none()
    if consent is None:
        raise NotFoundError("Consent record not found")

    consent.granted = granted
    consent.version += 1
    if not granted:
        consent.withdrawn_at = datetime.now(timezone.utc)

    await session.flush()
    logger.info("consent_updated", user_id=str(current_user.id), consent_id=str(consent_id), granted=granted)
    return {
        "id": str(consent.id),
        "consent_type": consent.consent_type,
        "granted": consent.granted,
        "version": consent.version,
        "withdrawn_at": consent.withdrawn_at.isoformat() if consent.withdrawn_at else None,
    }


@router.delete("/{consent_id}", status_code=204)
async def delete_consent(
    consent_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    stmt = select(Consent).where(Consent.id == consent_id, Consent.user_id == current_user.id)
    result = await session.execute(stmt)
    consent = result.scalar_one_or_none()
    if consent is None:
        raise NotFoundError("Consent record not found")

    await session.delete(consent)
    await session.flush()
    logger.info("consent_deleted", user_id=str(current_user.id), consent_id=str(consent_id))


@router.get("/history")
async def consent_history(
    consent_type: str | None = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    stmt = select(Consent).where(Consent.user_id == current_user.id)
    if consent_type:
        stmt = stmt.where(Consent.consent_type == consent_type)
    stmt = stmt.order_by(Consent.granted_at.desc())
    result = await session.execute(stmt)
    consents = result.scalars().all()

    return {
        "items": [
            {
                "id": str(c.id),
                "consent_type": c.consent_type,
                "granted": c.granted,
                "granted_at": c.granted_at.isoformat(),
                "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None,
                "version": c.version,
                "ip_address": c.ip_address,
            }
            for c in consents
        ],
        "total": len(consents),
    }
