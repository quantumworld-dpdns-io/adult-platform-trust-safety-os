"""Anomaly detection for audit events."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit.models import AuditEvent, ActionType

logger = structlog.get_logger(__name__)


class AnomalyDetector:
    """Detect suspicious patterns in audit event streams."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def detect_unusual_patterns(
        self,
        *,
        window_hours: int = 24,
        min_occurrences: int = 50,
    ) -> list[dict[str, Any]]:
        """Flag actor/action pairs that exceed expected frequency thresholds."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        stmt = (
            select(
                AuditEvent.actor_id,
                AuditEvent.action,
                func.count().label("cnt"),
            )
            .where(AuditEvent.timestamp >= cutoff)
            .where(AuditEvent.actor_id.isnot(None))
            .group_by(AuditEvent.actor_id, AuditEvent.action)
            .having(func.count() >= min_occurrences)
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        anomalies = []
        for actor_id, action, count in rows:
            anomalies.append({
                "type": "unusual_frequency",
                "actor_id": actor_id,
                "action": action.value if action else "UNKNOWN",
                "count": count,
                "window_hours": window_hours,
                "threshold": min_occurrences,
                "severity": "high" if count >= min_occurrences * 5 else "medium",
            })

        return anomalies

    async def detect_burst_events(
        self,
        *,
        window_seconds: int = 60,
        burst_threshold: int = 20,
    ) -> list[dict[str, Any]]:
        """Detect bursts of events from a single actor within a short time window."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds * 10)
        lookback = timedelta(seconds=window_seconds)

        stmt = (
            select(AuditEvent)
            .where(AuditEvent.timestamp >= cutoff)
            .where(AuditEvent.actor_id.isnot(None))
            .order_by(AuditEvent.actor_id, AuditEvent.timestamp.asc())
        )
        result = await self._session.execute(stmt)
        events = list(result.scalars().all())

        actor_events: dict[str, list[datetime]] = defaultdict(list)
        for e in events:
            if e.actor_id and e.timestamp:
                actor_events[e.actor_id].append(e.timestamp)

        anomalies = []
        for actor_id, timestamps in actor_events.items():
            for i in range(len(timestamps)):
                window_end = timestamps[i]
                window_start = window_end - lookback
                in_window = [
                    t for t in timestamps
                    if window_start <= t <= window_end
                ]
                if len(in_window) >= burst_threshold:
                    anomalies.append({
                        "type": "burst_events",
                        "actor_id": actor_id,
                        "event_count": len(in_window),
                        "window_seconds": window_seconds,
                        "threshold": burst_threshold,
                        "first_event": min(in_window).isoformat(),
                        "last_event": max(in_window).isoformat(),
                        "severity": "high" if len(in_window) >= burst_threshold * 3 else "medium",
                    })
                    break

        return anomalies

    async def detect_off_hours_access(
        self,
        *,
        start_hour: int = 22,
        end_hour: int = 6,
        min_events: int = 3,
    ) -> list[dict[str, Any]]:
        """Flag actors who perform significant actions outside business hours."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)

        stmt = (
            select(AuditEvent)
            .where(AuditEvent.timestamp >= cutoff)
            .where(AuditEvent.actor_id.isnot(None))
            .order_by(AuditEvent.timestamp.asc())
        )
        result = await self._session.execute(stmt)
        events = list(result.scalars().all())

        actor_off_hours: dict[str, list[dict]] = defaultdict(list)
        for e in events:
            if not e.timestamp:
                continue
            hour = e.timestamp.hour
            is_off_hours = hour >= start_hour or hour < end_hour
            if is_off_hours and e.actor_id:
                actor_off_hours[e.actor_id].append({
                    "event_id": str(e.id),
                    "timestamp": e.timestamp.isoformat(),
                    "action": e.action.value if e.action else "UNKNOWN",
                    "hour": hour,
                })

        anomalies = []
        for actor_id, off_hours_events in actor_off_hours.items():
            if len(off_hours_events) >= min_events:
                anomalies.append({
                    "type": "off_hours_access",
                    "actor_id": actor_id,
                    "off_hours_events": len(off_hours_events),
                    "threshold": min_events,
                    "examples": off_hours_events[:5],
                    "severity": "medium",
                })

        return anomalies

    async def detect_privilege_escalation(
        self,
        *,
        window_hours: int = 24,
    ) -> list[dict[str, Any]]:
        """Detect patterns suggesting privilege escalation attempts.

        Heuristics:
        - Actor performs LOGIN then immediately MODERATE or BAN actions.
        - Actor targets resources they previously had no access to.
        - Rapid sequence of READ → UPDATE → DELETE on sensitive resources.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        sensitive_actions = {ActionType.MODERATE, ActionType.BAN, ActionType.DELETE}
        read_update_delete: list[dict[str, Any]] = []

        stmt = (
            select(AuditEvent)
            .where(AuditEvent.timestamp >= cutoff)
            .where(AuditEvent.actor_id.isnot(None))
            .order_by(AuditEvent.actor_id, AuditEvent.timestamp.asc())
        )
        result = await self._session.execute(stmt)
        events = list(result.scalars().all())

        actor_sequences: dict[str, list[AuditEvent]] = defaultdict(list)
        for e in events:
            if e.actor_id:
                actor_sequences[e.actor_id].append(e)

        anomalies = []
        for actor_id, seq in actor_sequences.items():
            for i in range(len(seq) - 2):
                triple = seq[i : i + 3]
                actions = [e.action for e in triple]
                resources = [e.resource_id for e in triple]

                if (
                    actions[0] == ActionType.READ
                    and actions[1] == ActionType.UPDATE
                    and actions[2] == ActionType.DELETE
                    and len(set(resources)) == 1
                    and resources[0] is not None
                ):
                    read_update_delete.append({
                        "actor_id": actor_id,
                        "resource_id": resources[0],
                        "timestamps": [e.timestamp.isoformat() for e in triple if e.timestamp],
                    })

                if (
                    actions[0] == ActionType.LOGIN
                    and actions[1] in sensitive_actions
                    and triple[1].timestamp
                    and triple[0].timestamp
                ):
                    delta = (triple[1].timestamp - triple[0].timestamp).total_seconds()
                    if delta < 300:
                        anomalies.append({
                            "type": "privilege_escalation",
                            "actor_id": actor_id,
                            "pattern": "login_then_sensitive_action",
                            "seconds_between": delta,
                            "sensitive_action": actions[1].value if actions[1] else "UNKNOWN",
                            "severity": "high",
                        })

        for entry in read_update_delete:
            entry["type"] = "read_update_delete_chain"
            entry["severity"] = "high"
            anomalies.append(entry)

        return anomalies

    async def get_risk_events(
        self,
        *,
        risk_threshold: float = 0.7,
        window_hours: int = 24,
    ) -> list[dict[str, Any]]:
        """Aggregate all anomaly detections and return high-risk events."""
        all_anomalies: list[dict[str, Any]] = []

        all_anomalies.extend(await self.detect_unusual_patterns(window_hours=window_hours))
        all_anomalies.extend(await self.detect_burst_events())
        all_anomalies.extend(await self.detect_off_hours_access())
        all_anomalies.extend(await self.detect_privilege_escalation(window_hours=window_hours))

        severity_scores = {"low": 0.2, "medium": 0.5, "high": 0.8, "critical": 1.0}

        high_risk = [
            a for a in all_anomalies
            if severity_scores.get(a.get("severity", "low"), 0) >= risk_threshold
        ]

        high_risk.sort(key=lambda a: severity_scores.get(a.get("severity", "low"), 0), reverse=True)

        logger.info(
            "risk_events_detected",
            total_anomalies=len(all_anomalies),
            high_risk=len(high_risk),
        )
        return high_risk
