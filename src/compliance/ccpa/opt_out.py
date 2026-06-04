"""CCPA opt-out management: sale opt-out, opt-in, and status tracking."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_opt_out_store: dict[str, dict[str, Any]] = {}


class CCPAOptOut:
    def __init__(self) -> None:
        self._store = _opt_out_store

    async def opt_out_sale(
        self,
        user_id: str,
        categories: list[str] | None = None,
        method: str = "web_form",
    ) -> dict[str, Any]:
        record_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        sale_categories = categories or [
            "personal_info", "browsing_history", "purchase_history",
            "location_data", "demographic_data",
        ]

        record = {
            "record_id": record_id,
            "user_id": user_id,
            "status": "opted_out",
            "categories": sale_categories,
            "method": method,
            "opted_out_at": now,
            "opted_in_at": None,
            "last_verified_at": None,
        }
        self._store[user_id] = record

        logger.info("ccpa_opt_out", user_id=user_id, categories=sale_categories)

        return {
            "record_id": record_id,
            "status": "opted_out",
            "categories": sale_categories,
            "opted_out_at": now,
        }

    async def opt_in_sale(
        self,
        user_id: str,
        method: str = "web_form",
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()

        if user_id in self._store:
            record = self._store[user_id]
            record["status"] = "opted_in"
            record["opted_in_at"] = now
        else:
            record_id = str(uuid.uuid4())
            record = {
                "record_id": record_id,
                "user_id": user_id,
                "status": "opted_in",
                "categories": [],
                "method": method,
                "opted_out_at": None,
                "opted_in_at": now,
                "last_verified_at": None,
            }
            self._store[user_id] = record

        logger.info("ccpa_opt_in", user_id=user_id)

        return {
            "status": "opted_in",
            "opted_in_at": now,
        }

    async def get_opt_out_status(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        if user_id not in self._store:
            return {
                "user_id": user_id,
                "status": "no_preference_recorded",
                "is_opted_out": False,
            }

        record = self._store[user_id]
        is_expired = False
        if record.get("last_verified_at"):
            verified = datetime.fromisoformat(record["last_verified_at"])
            from datetime import timedelta
            if datetime.now(timezone.utc) - verified > timedelta(days=12):
                is_expired = True

        return {
            "user_id": user_id,
            "status": record["status"],
            "is_opted_out": record["status"] == "opted_out",
            "categories": record["categories"],
            "opted_out_at": record["opted_out_at"],
            "opted_in_at": record["opted_in_at"],
            "verification_needed": is_expired,
        }

    async def apply_opt_out_to_data(
        self,
        user_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        status = await self.get_opt_out_status(user_id)

        if not status["is_opted_out"]:
            return {"filtered_data": data, "filter_applied": False}

        categories = set(status.get("categories", []))
        filtered = {}
        for key, value in data.items():
            key_lower = key.lower().replace(" ", "_")
            should_filter = any(
                cat in key_lower or key_lower in cat
                for cat in categories
            )
            if not should_filter:
                filtered[key] = value

        return {
            "filtered_data": filtered,
            "filter_applied": True,
            "filtered_keys": [k for k in data if k not in filtered],
        }
