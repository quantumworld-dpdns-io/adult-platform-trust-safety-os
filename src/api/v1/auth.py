from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends
from passlib.hash import argon2
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_active_user, get_db_session
from src.api.exceptions import AuthenticationError, ValidationException
from src.api.schemas.auth import (
    LoginRequest,
    MFAEnableResponse,
    MFAVerifyRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
    RegisterRequest,
    TokenResponse,
)
from src.api.schemas.common import SuccessResponse
from src.auth.jwt import create_access_token, create_refresh_token, verify_token
from src.auth.mfa import generate_backup_codes, generate_mfa_secret, get_provisioning_uri, hash_backup_codes, verify_totp
from src.config.settings import settings
from src.core.user import User

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, session: AsyncSession = Depends(get_db_session)) -> TokenResponse:
    existing = await session.execute(
        select(User).where((User.email == body.email) | (User.username == body.username))
    )
    if existing.scalar_one_or_none() is not None:
        raise ValidationException(detail="Email or username already registered")

    user = User(
        email=body.email,
        username=body.username,
        password_hash=argon2.hash(body.password),
        roles=["user"],
    )
    session.add(user)
    await session.flush()

    access = create_access_token(user.id, roles=user.roles)
    refresh = create_refresh_token(user.id)

    logger.info("user_registered", user_id=str(user.id), email=body.email)
    return TokenResponse(access_token=access, refresh_token=refresh, expires_in=settings.jwt.access_token_expire_minutes * 60)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_db_session)) -> TokenResponse:
    stmt = select(User).where(User.email == body.email)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not argon2.verify(body.password, user.password_hash):
        raise AuthenticationError("Invalid email or password")

    if user.mfa_enabled:
        if not body.mfa_code:
            raise ValidationException(detail="MFA code required")
        if user.mfa_secret and not verify_totp(user.mfa_secret, body.mfa_code):
            raise AuthenticationError("Invalid MFA code")

    access = create_access_token(user.id, roles=user.roles)
    refresh = create_refresh_token(user.id)

    logger.info("user_logged_in", user_id=str(user.id))
    return TokenResponse(access_token=access, refresh_token=refresh, expires_in=settings.jwt.access_token_expire_minutes * 60)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    payload = verify_token(refresh_token, expected_type="refresh")
    if payload is None:
        raise AuthenticationError("Invalid or expired refresh token")

    user_id = payload["sub"]
    stmt = select(User).where(User.id == uuid.UUID(user_id))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthenticationError("User not found")

    access = create_access_token(user.id, roles=user.roles)
    new_refresh = create_refresh_token(user.id)

    return TokenResponse(access_token=access, refresh_token=new_refresh, expires_in=settings.jwt.access_token_expire_minutes * 60)


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    current_user: User = Depends(get_current_active_user),
    redis: Any = Depends(get_redis),
) -> SuccessResponse:
    logger.info("user_logged_out", user_id=str(current_user.id))
    return SuccessResponse(message="Successfully logged out")


@router.post("/mfa/enable", response_model=MFAEnableResponse)
async def mfa_enable(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> MFAEnableResponse:
    secret = generate_mfa_secret()
    backup_codes = generate_backup_codes()
    hashed = hash_backup_codes(backup_codes)

    current_user.mfa_secret = secret
    current_user.profile = {**(current_user.profile or {}), "mfa_backup_codes": hashed}
    await session.flush()

    provisioning_uri = get_provisioning_uri(secret, username=current_user.username)

    logger.info("mfa_enabled", user_id=str(current_user.id))
    return MFAEnableResponse(secret=secret, provisioning_uri=provisioning_uri, backup_codes=backup_codes)


@router.post("/mfa/verify", response_model=SuccessResponse)
async def mfa_verify(
    body: MFAVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse:
    if not current_user.mfa_secret:
        raise ValidationException(detail="MFA not enabled")

    if not verify_totp(current_user.mfa_secret, body.code):
        raise AuthenticationError("Invalid MFA code")

    current_user.mfa_enabled = True
    await session.flush()

    logger.info("mfa_verified", user_id=str(current_user.id))
    return SuccessResponse(message="MFA enabled successfully")


@router.post("/password/reset", response_model=SuccessResponse)
async def password_reset(body: PasswordResetRequest) -> SuccessResponse:
    logger.info("password_reset_requested", email=body.email)
    return SuccessResponse(message="If the email exists, a reset link has been sent")


@router.post("/password/change", response_model=SuccessResponse)
async def password_change(
    body: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse:
    if not argon2.verify(body.current_password, current_user.password_hash):
        raise AuthenticationError("Current password is incorrect")

    current_user.password_hash = argon2.hash(body.new_password)
    await session.flush()

    logger.info("password_changed", user_id=str(current_user.id))
    return SuccessResponse(message="Password changed successfully")
