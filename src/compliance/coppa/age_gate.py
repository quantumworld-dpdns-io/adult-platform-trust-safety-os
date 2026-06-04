"""COPPA age gating: age verification, parental consent, and data limits for children."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_child_store: dict[str, dict[str, Any]] = {}
_parental_consent_store: dict[str, dict[str, Any]] = {}

COPPA_AGE_THRESHOLD = 13
MAX_DATA_CATEGORIES = {"browsing", "location"}
BLOCKED_DATA_CATEGORIES = {"browsing_history", "location_data", "ad_targeting", "analytics"}


class COPPAAgeGate:
    def __init__(self) -> None:
        self._children = _child_store
        self._parental = _parental_consent_store

    async def verify_age(
        self,
        user_id: str,
        date_of_birth: str | None = None,
        declared_age: int | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)

        if date_of_birth:
            dob = datetime.fromisoformat(date_of_birth)
            age_days = (now - dob).days
            age_years = age_days // 365
            method = "date_of_birth"
        elif declared_age is not None:
            age_years = declared_age
            method = "declared_age"
        else:
            return {
                "user_id": user_id,
                "is_child": None,
                "error": "No age information provided",
            }

        is_child = age_years < COPPA_AGE_THRESHOLD

        record = {
            "user_id": user_id,
            "age_years": age_years,
            "is_child": is_child,
            "verification_method": method,
            "verified_at": now.isoformat(),
        }
        self._children[user_id] = record

        if is_child:
            logger.info("coppa_child_detected", user_id=user_id, age=age_years)

        return {
            "user_id": user_id,
            "is_child": is_child,
            "age_years": age_years,
            "coppa_threshold": COPPA_AGE_THRESHOLD,
            "verification_method": method,
            "verified_at": now.isoformat(),
        }

    async def check_parental_consent(
        self,
        user_id: str,
        parent_id: str | None = None,
    ) -> dict[str, Any]:
        consent_key = f"{user_id}:{parent_id}" if parent_id else user_id

        if consent_key in self._parental_consent:
            record = self._parental_consent_store[consent_key]
            return {
                "user_id": user_id,
                "has_parental_consent": True,
                "parent_id": record["parent_id"],
                "consented_at": record["consented_at"],
                "verification_method": record.get("verification_method", "email"),
            }

        return {
            "user_id": user_id,
            "has_parental_consent": False,
            "requires_consent": True,
        }

    async def enforce_data_limits(
        self,
        user_id: str,
        requested_data: list[str],
    ) -> dict[str, Any]:
        child_record = self._children.get(user_id)
        if child_record is None or not child_record.get("is_child"):
            return {
                "user_id": user_id,
                "filtered_data": requested_data,
                "blocked": [],
                "enforcement_applied": False,
            }

        consent_key = user_id
        has_consent = consent_key in self._parental_consent_store

        if has_consent:
            return {
                "user_id": user_id,
                "filtered_data": requested_data,
                "blocked": [],
                "enforcement_applied": True,
                "parental_consent": True,
            }

        allowed = []
        blocked = []
        for data_item in requested_data:
            data_lower = data_item.lower().replace(" ", "_")
            if any(blocked_cat in data_lower or data_lower in blocked_cat for blocked_cat in BLOCKED_DATA_CATEGORIES):
                blocked.append(data_item)
            else:
                allowed.append(data_item)

        return {
            "user_id": user_id,
            "filtered_data": allowed,
            "blocked": blocked,
            "enforcement_applied": True,
            "parental_consent": False,
        }

    async def get_coppa_status(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        child_record = self._children.get(user_id)
        parental_record = self._parental_consent_store.get(user_id)

        if child_record is None:
            return {
                "user_id": user_id,
                "age_verified": False,
                "is_child": None,
                "has_parental_consent": False,
                "coppa_applies": None,
            }

        return {
            "user_id": user_id,
            "age_verified": True,
            "is_child": child_record["is_child"],
            "age_years": child_record.get("age_years"),
            "has_parental_consent": parental_record is not None,
            "coppa_applies": child_record["is_child"],
            "verification_method": child_record.get("verification_method"),
            "verified_at": child_record.get("verified_at"),
        }
