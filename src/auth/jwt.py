"""JWT token creation and validation using RS256/ES256."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from src.config.settings import settings


def _load_key(key_path: str | None) -> str | bytes | None:
    if key_path is None:
        return None
    from pathlib import Path
    p = Path(key_path)
    if not p.exists():
        return None
    return p.read_bytes()


_jwt_settings = settings.jwt
_private_key = _load_key(_jwt_settings.private_key_path) or _jwt_settings.private_key_path
_public_key = _load_key(_jwt_settings.public_key_path) or _jwt_settings.public_key_path

ALGORITHM = _jwt_settings.algorithm
ACCESS_TOKEN_EXPIRE = timedelta(minutes=_jwt_settings.access_token_expire_minutes)
REFRESH_TOKEN_EXPIRE = timedelta(days=_jwt_settings.refresh_token_expire_days)


def create_access_token(
    subject: str | uuid.UUID,
    *,
    roles: list[str] | None = None,
    tenant_id: str | None = None,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or ACCESS_TOKEN_EXPIRE)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    if roles is not None:
        payload["roles"] = roles
    if tenant_id is not None:
        payload["tid"] = tenant_id
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, _private_key, algorithm=ALGORITHM)


def create_refresh_token(
    subject: str | uuid.UUID,
    *,
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or REFRESH_TOKEN_EXPIRE)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, _private_key, algorithm=ALGORITHM)


def verify_token(token: str, *, expected_type: str = "access") -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, _public_key, algorithms=[ALGORITHM])
    except JWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    return payload


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, _public_key, algorithms=[ALGORITHM])
    except JWTError:
        return None


def refresh_access_token(
    refresh_token: str,
    *,
    roles: list[str] | None = None,
    tenant_id: str | None = None,
) -> str | None:
    payload = verify_token(refresh_token, expected_type="refresh")
    if payload is None:
        return None
    return create_access_token(
        subject=payload["sub"],
        roles=roles,
        tenant_id=tenant_id,
    )
