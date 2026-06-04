from __future__ import annotations

import asyncio
import logging
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

RISK_WEIGHTS = {
    "age_verification_failure": 30.0,
    "multiple_failed_logins": 15.0,
    "rapid_content_creation": 10.0,
    "flagged_content_history": 20.0,
    "new_account_high_activity": 8.0,
    "vpn_or_proxy_usage": 5.0,
    "multiple_devices": 7.0,
    "consent_withdrawal": 10.0,
    "report_against_user": 25.0,
    "suspicious_session_pattern": 12.0,
}

RISK_THRESHOLD_LOW = 20.0
RISK_THRESHOLD_MEDIUM = 50.0
RISK_THRESHOLD_HIGH = 80.0


@dataclass
class RiskFactor:
    name: str
    score: float
    weight: float
    details: dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RiskAssessment:
    user_id: uuid.UUID
    total_score: float
    level: str
    factors: list[RiskFactor]
    assessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    recommendations: list[str] = field(default_factory=list)


class RiskScoreService:
    def __init__(self, *, storage: dict[str, Any] | None = None) -> None:
        self._storage: dict[str, Any] = storage or {}
        self._weights = dict(RISK_WEIGHTS)

    async def calculate_risk(
        self,
        user_id: uuid.UUID,
        *,
        user_data: dict[str, Any] | None = None,
        session_data: list[dict[str, Any]] | None = None,
        content_data: dict[str, Any] | None = None,
    ) -> RiskAssessment:
        factors: list[RiskFactor] = []

        if user_data:
            user_factors = await self._evaluate_user_risks(user_id, user_data)
            factors.extend(user_factors)

        if session_data:
            session_factors = await self._evaluate_session_risks(user_id, session_data)
            factors.extend(session_factors)

        if content_data:
            content_factors = await self._evaluate_content_risks(user_id, content_data)
            factors.extend(content_factors)

        total_score = sum(f.score for f in factors)
        total_score = min(total_score, 100.0)

        level = self._classify_risk_level(total_score)
        recommendations = self._generate_recommendations(factors, level)

        assessment = RiskAssessment(
            user_id=user_id,
            total_score=total_score,
            level=level,
            factors=factors,
            recommendations=recommendations,
        )

        self._storage[str(user_id)] = assessment
        logger.info(
            "Risk assessment for user %s: score=%.1f level=%s factors=%d",
            user_id, total_score, level, len(factors),
        )

        return assessment

    async def get_cached_risk(self, user_id: uuid.UUID) -> RiskAssessment | None:
        return self._storage.get(str(user_id))

    async def record_risk_event(
        self,
        user_id: uuid.UUID,
        event_name: str,
        event_data: dict[str, Any] | None = None,
    ) -> RiskAssessment | None:
        weight = self._weights.get(event_name, 5.0)
        existing = self._storage.get(str(user_id))

        if existing is None:
            factors = [
                RiskFactor(
                    name=event_name,
                    score=weight,
                    weight=weight,
                    details=event_data or {},
                )
            ]
            total = min(weight, 100.0)
            return RiskAssessment(
                user_id=user_id,
                total_score=total,
                level=self._classify_risk_level(total),
                factors=factors,
                recommendations=[],
            )

        new_factor = RiskFactor(
            name=event_name,
            score=weight,
            weight=weight,
            details=event_data or {},
        )
        existing.factors.append(new_factor)
        existing.total_score = min(
            sum(f.score for f in existing.factors), 100.0
        )
        existing.level = self._classify_risk_level(existing.total_score)
        existing.recommendations = self._generate_recommendations(
            existing.factors, existing.level
        )

        logger.info(
            "Risk updated for user %s: new event=%s total=%.1f",
            user_id, event_name, existing.total_score,
        )
        return existing

    async def _evaluate_user_risks(
        self, user_id: uuid.UUID, user_data: dict[str, Any]
    ) -> list[RiskFactor]:
        factors: list[RiskFactor] = []

        if user_data.get("age_verification_failures", 0) > 0:
            factors.append(
                RiskFactor(
                    name="age_verification_failure",
                    score=self._weights["age_verification_failure"],
                    weight=self._weights["age_verification_failure"],
                    details={"failures": user_data["age_verification_failures"]},
                )
            )

        if user_data.get("failed_login_count", 0) >= 3:
            factors.append(
                RiskFactor(
                    name="multiple_failed_logins",
                    score=min(user_data["failed_login_count"] * 5, self._weights["multiple_failed_logins"]),
                    weight=self._weights["multiple_failed_logins"],
                    details={"count": user_data["failed_login_count"]},
                )
            )

        if user_data.get("report_count", 0) > 0:
            factors.append(
                RiskFactor(
                    name="report_against_user",
                    score=min(
                        user_data["report_count"] * 10,
                        self._weights["report_against_user"],
                    ),
                    weight=self._weights["report_against_user"],
                    details={"reports": user_data["report_count"]},
                )
            )

        account_age_days = user_data.get("account_age_days")
        if account_age_days is not None and account_age_days < 7:
            activity_level = user_data.get("content_count", 0) + user_data.get("session_count", 0)
            if activity_level > 50:
                factors.append(
                    RiskFactor(
                        name="new_account_high_activity",
                        score=self._weights["new_account_high_activity"],
                        weight=self._weights["new_account_high_activity"],
                        details={
                            "account_age_days": account_age_days,
                            "activity_level": activity_level,
                        },
                    )
                )

        return factors

    async def _evaluate_session_risks(
        self, user_id: uuid.UUID, sessions: list[dict[str, Any]]
    ) -> list[RiskFactor]:
        factors: list[RiskFactor] = []

        unique_ips = {s.get("ip_address") for s in sessions if s.get("ip_address")}
        if len(unique_ips) > 3:
            factors.append(
                RiskFactor(
                    name="multiple_devices",
                    score=min(len(unique_ips) * 3, self._weights["multiple_devices"]),
                    weight=self._weights["multiple_devices"],
                    details={"unique_ips": len(unique_ips)},
                )
            )

        unique_fps = {s.get("device_fingerprint") for s in sessions if s.get("device_fingerprint")}
        if len(unique_fps) > 5:
            factors.append(
                RiskFactor(
                    name="suspicious_session_pattern",
                    score=self._weights["suspicious_session_pattern"],
                    weight=self._weights["suspicious_session_pattern"],
                    details={"unique_fingerprints": len(unique_fps)},
                )
            )

        vpn_count = sum(1 for s in sessions if s.get("is_vpn"))
        if vpn_count > 0:
            factors.append(
                RiskFactor(
                    name="vpn_or_proxy_usage",
                    score=self._weights["vpn_or_proxy_usage"],
                    weight=self._weights["vpn_or_proxy_usage"],
                    details={"vpn_sessions": vpn_count},
                )
            )

        return factors

    async def _evaluate_content_risks(
        self, user_id: uuid.UUID, content_data: dict[str, Any]
    ) -> list[RiskFactor]:
        factors: list[RiskFactor] = []

        flagged_count = content_data.get("flagged_count", 0)
        if flagged_count > 0:
            factors.append(
                RiskFactor(
                    name="flagged_content_history",
                    score=min(flagged_count * 5, self._weights["flagged_content_history"]),
                    weight=self._weights["flagged_content_history"],
                    details={"flagged_items": flagged_count},
                )
            )

        recent_count = content_data.get("recent_content_count", 0)
        time_window_minutes = content_data.get("time_window_minutes", 60)
        if time_window_minutes > 0 and recent_count / time_window_minutes > 1:
            factors.append(
                RiskFactor(
                    name="rapid_content_creation",
                    score=min(
                        (recent_count / max(time_window_minutes, 1)) * 5,
                        self._weights["rapid_content_creation"],
                    ),
                    weight=self._weights["rapid_content_creation"],
                    details={
                        "count": recent_count,
                        "window_minutes": time_window_minutes,
                    },
                )
            )

        return factors

    def _classify_risk_level(self, score: float) -> str:
        if score < RISK_THRESHOLD_LOW:
            return "low"
        if score < RISK_THRESHOLD_MEDIUM:
            return "medium"
        if score < RISK_THRESHOLD_HIGH:
            return "high"
        return "critical"

    def _generate_recommendations(
        self, factors: list[RiskFactor], level: str
    ) -> list[str]:
        recommendations: list[str] = []
        factor_names = {f.name for f in factors}

        if level in ("high", "critical"):
            recommendations.append("Consider temporary account restriction pending review.")

        if "age_verification_failure" in factor_names:
            recommendations.append("Require additional age verification before granting access.")

        if "multiple_failed_logins" in factor_names:
            recommendations.append("Enforce MFA and lock account after next failed attempt.")

        if "report_against_user" in factor_names:
            recommendations.append("Priority queue for moderation review.")

        if "vpn_or_proxy_usage" in factor_names:
            recommendations.append("Flag session for additional identity verification.")

        if "rapid_content_creation" in factor_names:
            recommendations.append("Rate-limit content creation and review recent uploads.")

        if "new_account_high_activity" in factor_names:
            recommendations.append("Restrict new account capabilities until trust is established.")

        if not recommendations:
            recommendations.append("Continue monitoring.")

        return recommendations
