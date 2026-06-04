"""MCP tools for user information, age verification, and risk scoring."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Any


_user_store: dict[str, dict[str, Any]] = {}


async def get_user_info(user_id: str) -> dict[str, Any]:
    if user_id not in _user_store:
        return {"error": "User not found", "user_id": user_id}
    return _user_store[user_id]


async def verify_user_age(
    user_id: str,
    date_of_birth: str | None = None,
    minimum_age: int = 18,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)

    if user_id in _user_store and _user_store[user_id].get("date_of_birth"):
        dob_str = _user_store[user_id]["date_of_birth"]
        dob = datetime.fromisoformat(dob_str)
        age_days = (now - dob).days
        age_years = age_days // 365
        is_verified = age_years >= minimum_age
        return {
            "user_id": user_id,
            "is_verified": is_verified,
            "age_years": age_years,
            "minimum_age": minimum_age,
            "verified_at": now.isoformat(),
            "method": "stored_dob",
        }

    if date_of_birth:
        dob = datetime.fromisoformat(date_of_birth)
        age_days = (now - dob).days
        age_years = age_days // 365
        is_verified = age_years >= minimum_age
        return {
            "user_id": user_id,
            "is_verified": is_verified,
            "age_years": age_years,
            "minimum_age": minimum_age,
            "verified_at": now.isoformat(),
            "method": "provided_dob",
        }

    return {
        "user_id": user_id,
        "is_verified": False,
        "error": "No date of birth available for verification",
        "minimum_age": minimum_age,
    }


async def get_user_risk_score(user_id: str) -> dict[str, Any]:
    if user_id not in _user_store:
        return {"error": "User not found", "user_id": user_id}

    user = _user_store[user_id]
    risk_factors: list[str] = []
    score = 0.0

    if user.get("failed_login_attempts", 0) > 3:
        risk_factors.append("multiple_failed_logins")
        score += 0.3

    if user.get("account_age_days", 365) < 7:
        risk_factors.append("new_account")
        score += 0.1

    if user.get("reports_against", 0) > 0:
        risk_factors.append("has_reports")
        score += 0.2 * min(user["reports_against"], 3)

    if user.get("is_age_verified") is not True:
        risk_factors.append("unverified_age")
        score += 0.2

    score = min(score, 1.0)

    risk_level = "low"
    if score > 0.7:
        risk_level = "critical"
    elif score > 0.5:
        risk_level = "high"
    elif score > 0.3:
        risk_level = "medium"

    return {
        "user_id": user_id,
        "risk_score": round(score, 2),
        "risk_level": risk_level,
        "risk_factors": risk_factors,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
