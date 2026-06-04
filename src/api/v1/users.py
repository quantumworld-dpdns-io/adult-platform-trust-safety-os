from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_active_user, get_db_session, require_role
from src.api.exceptions import NotFoundError, ValidationException
from src.api.schemas.user import (
    AgeVerificationRequest,
    AgeVerificationResponse,
    RiskFactorItem,
    RiskScoreResponse,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from src.core.age_verification import AgeVerificationService, VerificationMethod
from src.core.risk_score import RiskScoreService
from src.core.user import User

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> UserListResponse:
    total = (await session.execute(select(func.count()).select_from(User))).scalar() or 0
    offset = (page - 1) * per_page
    stmt = select(User).order_by(User.created_at.desc()).offset(offset).limit(per_page)
    result = await session.execute(stmt)
    users = result.scalars().all()

    items = [UserResponse.model_validate(u) for u in users]
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    return UserListResponse(items=items, total=total, page=page, per_page=per_page, pages=pages)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    if body.email is not None:
        existing = await session.execute(select(User).where(User.email == body.email, User.id != current_user.id))
        if existing.scalar_one_or_none():
            raise ValidationException(detail="Email already in use")
        current_user.email = body.email
    if body.username is not None:
        existing = await session.execute(select(User).where(User.username == body.username, User.id != current_user.id))
        if existing.scalar_one_or_none():
            raise ValidationException(detail="Username already taken")
        current_user.username = body.username
    if body.profile is not None:
        current_user.profile = body.profile

    await session.flush()
    return UserResponse.model_validate(current_user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_role("admin", "moderator")),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found")
    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    current_user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found")

    if body.email is not None:
        user.email = body.email
    if body.username is not None:
        user.username = body.username
    if body.profile is not None:
        user.profile = body.profile

    await session.flush()
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", response_model=None, status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found")

    user.soft_delete()
    await session.flush()
    logger.info("user_deleted", user_id=str(user_id), actor=str(current_user.id))


@router.post("/{user_id}/verify-age", response_model=AgeVerificationResponse)
async def verify_age(
    user_id: uuid.UUID,
    body: AgeVerificationRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> AgeVerificationResponse:
    if str(current_user.id) != str(user_id) and "admin" not in (current_user.roles or []):
        from src.api.exceptions import AuthorizationError
        raise AuthorizationError("Can only verify your own age")

    svc = AgeVerificationService()
    method = VerificationMethod(body.method)

    if method == VerificationMethod.DOCUMENT:
        doc_data = bytes(body.document_data or "", "utf-8")
        result = await svc.verify_by_document(
            user_id, body.document_type or "unknown", doc_data, body.issued_country
        )
    elif method == VerificationMethod.ID_SCAN:
        id_image = bytes(body.id_image or "", "utf-8")
        result = await svc.verify_by_id_scan(user_id, id_image, body.barcode_data)
    else:
        raise ValidationException(detail=f"Unsupported verification method: {body.method}")

    if result.age_confirmed:
        stmt = select(User).where(User.id == user_id)
        db_result = await session.execute(stmt)
        user = db_result.scalar_one_or_none()
        if user:
            from datetime import datetime, timezone
            user.age_verified = True
            user.age_verified_at = datetime.now(timezone.utc)
            await session.flush()

    return AgeVerificationResponse(
        user_id=result.user_id,
        status=result.status.value,
        method=result.method.value,
        verified_at=result.verified_at,
        age_confirmed=result.age_confirmed,
        confidence=result.confidence,
        details=result.details,
        error=result.error,
    )


@router.get("/{user_id}/risk-score", response_model=RiskScoreResponse)
async def get_risk_score(
    user_id: uuid.UUID,
    current_user: User = Depends(require_role("admin", "moderator")),
    session: AsyncSession = Depends(get_db_session),
) -> RiskScoreResponse:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found")

    svc = RiskScoreService()
    assessment = await svc.calculate_risk(
        user_id,
        user_data={
            "age_verification_failures": 0 if user.age_verified else 1,
            "account_age_days": 30,
            "content_count": 10,
            "session_count": 5,
        },
    )

    factors = [
        RiskFactorItem(
            name=f.name,
            score=f.score,
            weight=f.weight,
            details=f.details,
            detected_at=f.detected_at,
        )
        for f in assessment.factors
    ]

    return RiskScoreResponse(
        user_id=assessment.user_id,
        total_score=assessment.total_score,
        level=assessment.level,
        factors=factors,
        assessed_at=assessment.assessed_at,
        recommendations=assessment.recommendations,
    )
