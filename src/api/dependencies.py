from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Any, Callable

import redis.asyncio as aioredis
import structlog
from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.exceptions import AuthenticationError, AuthorizationError
from src.auth.jwt import verify_token
from src.auth.rbac import ROLE_PERMISSIONS, Role
from src.config.settings import settings
from src.core.user import User

logger = structlog.get_logger(__name__)


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    session_factory = request.app.state.db_session_factory
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_redis(request: Request) -> AsyncGenerator[aioredis.Redis, None]:
    client: aioredis.Redis = request.app.state.redis
    yield client


async def get_current_user(
    authorization: str = Header(None, alias="Authorization"),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    payload = verify_token(token, expected_type="access")
    if payload is None:
        raise AuthenticationError("Invalid or expired access token")

    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError("Token missing subject claim")

    from sqlalchemy import select

    stmt = select(User).where(User.id == uuid.UUID(user_id))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise AuthenticationError("User not found")
    if not user.is_active:
        raise AuthenticationError("User account is deactivated")
    if user.is_banned:
        raise AuthenticationError("User account is banned")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise AuthenticationError("User account is deactivated")
    return current_user


def require_role(*roles: str) -> Callable[..., Any]:
    async def role_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        user_roles = {r.lower() for r in (current_user.roles or [])}
        required = {r.lower() for r in roles}
        if not user_roles.intersection(required):
            raise AuthorizationError(
                f"Required role: {' or '.join(roles)}"
            )
        return current_user
    return role_checker


async def get_audit_logger(
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    from src.audit.logger import AuditLogger
    return AuditLogger(session)
