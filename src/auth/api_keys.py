"""API key management with SHA-256 hash storage."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

KEY_PREFIX = "tsk_live_"
KEY_BYTES = 32


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _generate_raw_key() -> str:
    token = secrets.token_urlsafe(KEY_BYTES)
    return f"{KEY_PREFIX}{token}"


class APIKeyManager:
    def __init__(self) -> None:
        self._keys: dict[str, dict[str, Any]] = {}

    def generate_key(
        self,
        *,
        name: str,
        owner_id: str,
        scopes: list[str] | None = None,
        expires_in_days: int | None = None,
        rate_limit: int | None = None,
    ) -> dict[str, Any]:
        raw_key = _generate_raw_key()
        key_hash = _hash_key(raw_key)
        now = datetime.now(timezone.utc)
        key_data: dict[str, Any] = {
            "key_id": str(uuid.uuid4()),
            "name": name,
            "owner_id": owner_id,
            "key_hash": key_hash,
            "prefix": raw_key[:12] + "...",
            "scopes": scopes or [],
            "created_at": now.isoformat(),
            "expires_at": None,
            "rate_limit": rate_limit,
            "is_active": True,
            "last_used_at": None,
            "use_count": 0,
        }
        if expires_in_days is not None:
            from datetime import timedelta
            key_data["expires_at"] = (now + timedelta(days=expires_in_days)).isoformat()

        self._keys[key_hash] = key_data
        return {**key_data, "raw_key": raw_key}

    def validate_key(self, raw_key: str) -> tuple[bool, dict[str, Any] | None]:
        key_hash = _hash_key(raw_key)
        key_data = self._keys.get(key_hash)
        if key_data is None:
            return False, None
        if not key_data["is_active"]:
            return False, None
        if key_data["expires_at"] is not None:
            expires_at = datetime.fromisoformat(key_data["expires_at"])
            if expires_at < datetime.now(timezone.utc):
                return False, None
        now = datetime.now(timezone.utc)
        key_data["last_used_at"] = now.isoformat()
        key_data["use_count"] += 1
        return True, key_data

    def revoke_key(self, key_hash: str) -> bool:
        key_data = self._keys.get(key_hash)
        if key_data is None:
            return False
        key_data["is_active"] = False
        return True

    def list_keys(
        self,
        *,
        owner_id: str | None = None,
        include_revoked: bool = False,
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for key_data in self._keys.values():
            if owner_id and key_data["owner_id"] != owner_id:
                continue
            if not include_revoked and not key_data["is_active"]:
                continue
            result.append(key_data)
        return result

    def rotate_key(
        self,
        old_key_hash: str,
        *,
        expires_in_days: int | None = None,
    ) -> dict[str, Any] | None:
        old_data = self._keys.get(old_key_hash)
        if old_data is None:
            return None
        self.revoke_key(old_key_hash)
        new_key = self.generate_key(
            name=old_data["name"],
            owner_id=old_data["owner_id"],
            scopes=old_data["scopes"],
            expires_in_days=expires_in_days,
            rate_limit=old_data["rate_limit"],
        )
        return new_key
