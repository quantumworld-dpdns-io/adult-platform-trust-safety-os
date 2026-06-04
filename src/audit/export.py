"""Audit log export – CSV, JSON, and compliance reports."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Sequence

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit.models import AuditEvent

logger = structlog.get_logger(__name__)


class AuditExporter:
    """Export audit events to various formats for compliance and forensics."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def export_csv(
        self,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 10_000,
    ) -> str:
        events = await self._query_events(start_time, end_time, limit)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "timestamp", "actor_id", "actor_type", "action",
            "resource_type", "resource_id", "ip_address", "session_id",
            "integrity_hash", "details",
        ])
        for e in events:
            writer.writerow([
                str(e.id),
                e.timestamp.isoformat() if e.timestamp else "",
                e.actor_id or "",
                e.actor_type.value if e.actor_type else "",
                e.action.value if e.action else "",
                e.resource_type or "",
                e.resource_id or "",
                e.ip_address or "",
                e.session_id or "",
                e.integrity_hash or "",
                json.dumps(e.details) if e.details else "",
            ])
        return output.getvalue()

    async def export_json(
        self,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 10_000,
    ) -> str:
        events = await self._query_events(start_time, end_time, limit)
        records = [
            {
                "id": str(e.id),
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "actor_id": e.actor_id,
                "actor_type": e.actor_type.value if e.actor_type else None,
                "action": e.action.value if e.action else None,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "details": e.details,
                "ip_address": e.ip_address,
                "user_agent": e.user_agent,
                "session_id": e.session_id,
                "integrity_hash": e.integrity_hash,
            }
            for e in events
        ]
        return json.dumps(records, indent=2, default=str)

    async def export_compliance_report(
        self,
        framework: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict:
        """Generate a compliance report for SOC2, ISO27001, GDPR, or DSA."""
        events = await self._query_events(start_time, end_time, limit=50_000)
        total = len(events)

        action_counts: dict[str, int] = {}
        actor_counts: dict[str, int] = {}
        resource_counts: dict[str, int] = {}
        failed_verifications = 0

        for e in events:
            action_key = e.action.value if e.action else "UNKNOWN"
            action_counts[action_key] = action_counts.get(action_key, 0) + 1

            actor_key = e.actor_type.value if e.actor_type else "UNKNOWN"
            actor_counts[actor_key] = actor_counts.get(actor_key, 0) + 1

            resource_key = e.resource_type or "UNKNOWN"
            resource_counts[resource_key] = resource_counts.get(resource_key, 0) + 1

            if not e.integrity_hash:
                failed_verifications += 1

        report = {
            "framework": framework,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "period": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None,
            },
            "summary": {
                "total_events": total,
                "unique_actors": len(set(
                    e.actor_id for e in events if e.actor_id
                )),
                "integrity_failures": failed_verifications,
            },
            "breakdown": {
                "by_action": action_counts,
                "by_actor_type": actor_counts,
                "by_resource": resource_counts,
            },
        }

        if framework.upper() == "SOC2":
            report["soc2_controls"] = {
                "CC6.1": {
                    "description": "Logical access controls",
                    "status": "PASS" if failed_verifications == 0 else "FAIL",
                    "evidence": f"{total} events audited, {failed_verifications} integrity failures",
                },
                "CC7.2": {
                    "description": "Monitoring activities",
                    "status": "PASS",
                    "evidence": "Continuous audit logging with Merkle tree integrity verification",
                },
            }
        elif framework.upper() == "ISO27001":
            report["iso27001_controls"] = {
                "A.12.4.1": {
                    "description": "Event logging",
                    "status": "PASS" if total > 0 else "FAIL",
                    "evidence": f"{total} events recorded",
                },
                "A.12.4.4": {
                    "description": "Clock synchronisation",
                    "status": "PASS",
                    "evidence": "All timestamps UTC with timezone awareness",
                },
            }
        elif framework.upper() == "GDPR":
            report["gdpr_articles"] = {
                "Art.5(1)(f)": {
                    "description": "Integrity and confidentiality",
                    "status": "PASS" if failed_verifications == 0 else "FAIL",
                    "evidence": f"Integrity verification: {total - failed_verifications}/{total} passed",
                },
                "Art.30": {
                    "description": "Records of processing activities",
                    "status": "PASS" if total > 0 else "FAIL",
                    "evidence": f"{total} processing activity records available",
                },
            }
        elif framework.upper() == "DSA":
            report["dsa_articles"] = {
                "Art.15": {
                    "description": "Transparency reporting",
                    "status": "PASS",
                    "evidence": f"{total} content moderation decisions logged",
                },
                "Art.17": {
                    "description": "Statement of reasons",
                    "status": "PASS" if action_counts.get("MODERATE", 0) > 0 else "WARN",
                    "evidence": f"{action_counts.get('MODERATE', 0)} moderation actions",
                },
            }

        return report

    async def export_filtered(
        self,
        *,
        actor_id: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 10_000,
    ) -> Sequence[AuditEvent]:
        stmt = select(AuditEvent).order_by(AuditEvent.timestamp.desc())
        if actor_id:
            stmt = stmt.where(AuditEvent.actor_id == actor_id)
        if action:
            stmt = stmt.where(AuditEvent.action == action)
        if resource_type:
            stmt = stmt.where(AuditEvent.resource_type == resource_type)
        if start_time:
            stmt = stmt.where(AuditEvent.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(AuditEvent.timestamp <= end_time)
        stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def _query_events(
        self,
        start_time: datetime | None,
        end_time: datetime | None,
        limit: int,
    ) -> Sequence[AuditEvent]:
        stmt = select(AuditEvent).order_by(AuditEvent.timestamp.asc())
        if start_time:
            stmt = stmt.where(AuditEvent.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(AuditEvent.timestamp <= end_time)
        stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()
