"""GDPR consent management: record, query, withdraw, and audit consent."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_consent_store: dict[str, dict[str, Any]] = {}
_user_consents: dict[str, list[str]] = {}
_consent_history: list[dict[str, Any]] = []


class GDPRConsentManager:
    def __init__(self) -> None:
        self._consents = _consent_store
        self._user_map = _user_consents
        self._history = _consent_history

    async def record_consent(
        self,
        user_id: str,
        purpose: str,
        scope: list[str] | None = None,
        legal_basis: str = "consent",
        expires_in_days: int | None = None,
    ) -> dict[str, Any]:
        consent_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        from datetime import timedelta

        expires_at = None
        if expires_in_days:
            expires_at = (now + timedelta(days=expires_in_days)).isoformat()

        record = {
            "consent_id": consent_id,
            "user_id": user_id,
            "purpose": purpose,
            "scope": scope or ["data_processing"],
            "legal_basis": legal_basis,
            "status": "granted",
            "granted_at": now.isoformat(),
            "expires_at": expires_at,
            "withdrawn_at": None,
        }
        self._consents[consent_id] = record

        if user_id not in self._user_map:
            self._user_map[user_id] = []
        self._user_map[user_id].append(consent_id)

        history_entry = {
            "action": "granted",
            "consent_id": consent_id,
            "user_id": user_id,
            "purpose": purpose,
            "timestamp": now.isoformat(),
        }
        self._history.append(history_entry)

        logger.info("consent_recorded", user_id=user_id, consent_id=consent_id, purpose=purpose)

        return {
            "consent_id": consent_id,
            "status": "granted",
            "purpose": purpose,
            "granted_at": now.isoformat(),
            "expires_at": expires_at,
        }

    async def get_consent_status(
        self,
        user_id: str,
        purpose: str | None = None,
    ) -> dict[str, Any]:
        consent_ids = self._user_map.get(user_id, [])
        consents = []
        for cid in consent_ids:
            record = self._consents.get(cid)
            if record is None:
                continue
            if purpose and record["purpose"] != purpose:
                continue

            is_expired = False
            if record.get("expires_at"):
                expires = datetime.fromisoformat(record["expires_at"])
                is_expired = expires < datetime.now(timezone.utc)

            consents.append({
                "consent_id": cid,
                "purpose": record["purpose"],
                "status": record["status"],
                "scope": record["scope"],
                "granted_at": record["granted_at"],
                "expires_at": record["expires_at"],
                "is_expired": is_expired,
            })

        active = [c for c in consents if c["status"] == "granted" and not c["is_expired"]]

        return {
            "user_id": user_id,
            "total_consents": len(consents),
            "active_consents": len(active),
            "consents": consents,
        }

    async def withdraw_consent(
        self,
        user_id: str,
        consent_id: str,
        reason: str = "user_request",
    ) -> dict[str, Any]:
        if consent_id not in self._consents:
            return {"error": "Consent not found", "consent_id": consent_id}

        record = self._consents[consent_id]
        if record["user_id"] != user_id:
            return {"error": "Consent does not belong to user"}

        now = datetime.now(timezone.utc).isoformat()
        record["status"] = "withdrawn"
        record["withdrawn_at"] = now

        history_entry = {
            "action": "withdrawn",
            "consent_id": consent_id,
            "user_id": user_id,
            "purpose": record["purpose"],
            "reason": reason,
            "timestamp": now,
        }
        self._history.append(history_entry)

        logger.info("consent_withdrawn", user_id=user_id, consent_id=consent_id)

        return {
            "consent_id": consent_id,
            "status": "withdrawn",
            "withdrawn_at": now,
        }

    async def get_consent_history(
        self,
        user_id: str,
        limit: int = 50,
    ) -> dict[str, Any]:
        entries = [h for h in self._history if h["user_id"] == user_id]
        entries.sort(key=lambda x: x["timestamp"], reverse=True)

        return {
            "user_id": user_id,
            "history": entries[:limit],
            "total": len(entries),
        }
