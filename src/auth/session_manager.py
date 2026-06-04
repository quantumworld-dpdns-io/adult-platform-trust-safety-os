"""Server-side session management with Redis."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import redis.asyncio as redis

from src.config.settings import settings

SESSION_TTL = timedelta(hours=24)
REFRESH_TTL = timedelta(days=7)
KEY_PREFIX = "session:"


class SessionManager:
    def __init__(self, redis_client: redis.Redis | None = None) -> None:
        self._redis = redis_client or redis.from_url(
            settings.redis.url,
            max_connections=settings.redis.max_connections,
            decode_responses=True,
        )

    async def create_session(
        self,
        user_id: str,
        *,
        ip_address: str,
        user_agent: str | None = None,
        device_fingerprint: str | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        session_data: dict[str, Any] = {
            "session_id": session_id,
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent or "",
            "device_fingerprint": device_fingerprint or "",
            "created_at": now.isoformat(),
            "last_active_at": now.isoformat(),
            "expires_at": (now + SESSION_TTL).isoformat(),
            "is_active": True,
        }
        if extra_data:
            session_data.update(extra_data)

        key = f"{KEY_PREFIX}{session_id}"
        user_key = f"{KEY_PREFIX}user:{user_id}"

        pipe = self._redis.pipeline()
        pipe.set(key, json.dumps(session_data), ex=int(SESSION_TTL.total_seconds()))
        pipe.sadd(user_key, session_id)
        pipe.expire(user_key, int(REFRESH_TTL.total_seconds()))
        await pipe.execute()

        return session_data

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        key = f"{KEY_PREFIX}{session_id}"
        raw = await self._redis.get(key)
        if raw is None:
            return None
        data = json.loads(raw)
        if datetime.fromisoformat(data["expires_at"]) < datetime.now(timezone.utc):
            await self.invalidate_session(session_id)
            return None
        data["last_active_at"] = datetime.now(timezone.utc).isoformat()
        await self._redis.set(key, json.dumps(data), ex=int(SESSION_TTL.total_seconds()))
        return data

    async def invalidate_session(self, session_id: str) -> bool:
        key = f"{KEY_PREFIX}{session_id}"
        raw = await self._redis.get(key)
        if raw is None:
            return False
        data = json.loads(raw)
        user_key = f"{KEY_PREFIX}user:{data['user_id']}"
        pipe = self._redis.pipeline()
        pipe.delete(key)
        pipe.srem(user_key, session_id)
        await pipe.execute()
        return True

    async def refresh_session(
        self,
        session_id: str,
        *,
        extend_ttl: timedelta | None = None,
    ) -> dict[str, Any] | None:
        data = await self.get_session(session_id)
        if data is None:
            return None
        ttl = extend_ttl or SESSION_TTL
        new_expiry = datetime.now(timezone.utc) + ttl
        data["expires_at"] = new_expiry.isoformat()
        data["last_active_at"] = datetime.now(timezone.utc).isoformat()
        key = f"{KEY_PREFIX}{session_id}"
        await self._redis.set(key, json.dumps(data), ex=int(ttl.total_seconds()))
        return data

    async def get_active_sessions(self, user_id: str) -> list[dict[str, Any]]:
        user_key = f"{KEY_PREFIX}user:{user_id}"
        session_ids = await self._redis.smembers(user_key)
        sessions: list[dict[str, Any]] = []
        for sid in session_ids:
            data = await self.get_session(sid)
            if data and data.get("is_active"):
                sessions.append(data)
        return sessions

    async def close(self) -> None:
        await self._redis.aclose()
