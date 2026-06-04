from __future__ import annotations

import time
import uuid

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session, require_role
from src.api.exceptions import NotFoundError
from src.api.schemas.common import SuccessResponse
from src.api.schemas.user import UserResponse
from src.config.settings import settings
from src.core.user import User
from src.audit.models import AuditEvent

logger = structlog.get_logger(__name__)

START_TIME = time.monotonic()

router = APIRouter()


@router.get("/stats")
async def admin_stats(
    current_user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    total_users = (await session.execute(select(func.count()).select_from(User))).scalar() or 0
    active_users = (
        await session.execute(
            select(func.count()).select_from(User).where(User.is_active == True)
        )
    ).scalar() or 0
    banned_users = (
        await session.execute(
            select(func.count()).select_from(User).where(User.is_banned == True)
        )
    ).scalar() or 0
    verified_users = (
        await session.execute(
            select(func.count()).select_from(User).where(User.age_verified == True)
        )
    ).scalar() or 0
    mfa_users = (
        await session.execute(
            select(func.count()).select_from(User).where(User.mfa_enabled == True)
        )
    ).scalar() or 0

    return {
        "total_users": total_users,
        "active_users": active_users,
        "banned_users": banned_users,
        "verified_users": verified_users,
        "mfa_enabled_users": mfa_users,
    }


@router.get("/users", response_model=list[UserResponse])
async def admin_list_users(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> list[UserResponse]:
    offset = (page - 1) * per_page
    stmt = select(User).order_by(User.created_at.desc()).offset(offset).limit(per_page)
    result = await session.execute(stmt)
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.put("/users/{user_id}/ban")
async def ban_user(
    user_id: uuid.UUID,
    reason: str = Query(default="No reason provided"),
    current_user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found")

    user.is_banned = True
    user.ban_reason = reason
    user.is_active = False
    await session.flush()

    logger.info("user_banned", user_id=str(user_id), reason=reason, actor=str(current_user.id))
    return SuccessResponse(message=f"User {user_id} has been banned")


@router.get("/system-health")
async def system_health(
    current_user: User = Depends(require_role("admin")),
) -> dict:
    uptime = round(time.monotonic() - START_TIME, 2)
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.app_env,
        "uptime_seconds": uptime,
        "database": settings.database.url.split("@")[-1] if "@" in settings.database.url else "configured",
        "redis": settings.redis.url,
        "qdrant": settings.qdrant.url,
        "ollama": settings.ollama.base_url,
    }


@router.get("/audit-logs")
async def admin_audit_logs(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    total = (await session.execute(select(func.count()).select_from(AuditEvent))).scalar() or 0
    offset = (page - 1) * per_page
    stmt = select(AuditEvent).order_by(AuditEvent.timestamp.desc()).offset(offset).limit(per_page)
    result = await session.execute(stmt)
    events = result.scalars().all()

    pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    return {
        "items": [
            {
                "id": str(e.id),
                "timestamp": e.timestamp.isoformat(),
                "actor_id": e.actor_id,
                "actor_type": e.actor_type.value,
                "action": e.action.value,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "ip_address": e.ip_address,
            }
            for e in events
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
    }
