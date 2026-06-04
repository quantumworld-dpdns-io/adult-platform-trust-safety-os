"""Audit log retention and archival management."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import delete, func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit.models import AuditEvent

logger = structlog.get_logger(__name__)


class RetentionManager:
    """Enforce data retention policies and archive old audit events."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._policies: dict[str, dict[str, Any]] = {
            "default": {"retention_days": 365, "archive": True},
            "security": {"retention_days": 730, "archive": True},
            "compliance": {"retention_days": 2555, "archive": True},
        }

    def configure_retention(
        self,
        policy_name: str,
        *,
        retention_days: int,
        archive: bool = True,
    ) -> None:
        """Add or update a retention policy."""
        self._policies[policy_name] = {
            "retention_days": retention_days,
            "archive": archive,
        }
        logger.info(
            "retention_policy_configured",
            policy=policy_name,
            retention_days=retention_days,
            archive=archive,
        )

    async def apply_retention_policy(
        self,
        policy_name: str = "default",
        *,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Delete events older than the retention period for the given policy."""
        policy = self._policies.get(policy_name)
        if not policy:
            raise ValueError(f"Unknown retention policy: {policy_name}")

        cutoff = datetime.now(timezone.utc) - timedelta(days=policy["retention_days"])

        count_stmt = (
            select(func.count())
            .select_from(AuditEvent)
            .where(AuditEvent.timestamp < cutoff)
        )
        affected_count = (await self._session.execute(count_stmt)).scalar() or 0

        if dry_run or affected_count == 0:
            return {
                "policy": policy_name,
                "cutoff_date": cutoff.isoformat(),
                "affected_events": affected_count,
                "deleted": 0,
                "archived": 0,
                "dry_run": dry_run,
            }

        archived = 0
        if policy["archive"]:
            archived = await self._archive_events(cutoff)

        delete_stmt = (
            delete(AuditEvent)
            .where(AuditEvent.timestamp < cutoff)
        )
        result = await self._session.execute(delete_stmt)
        deleted = result.rowcount

        logger.info(
            "retention_policy_applied",
            policy=policy_name,
            deleted=deleted,
            archived=archived,
        )
        return {
            "policy": policy_name,
            "cutoff_date": cutoff.isoformat(),
            "affected_events": affected_count,
            "deleted": deleted,
            "archived": archived,
            "dry_run": False,
        }

    async def archive_old_events(
        self,
        *,
        older_than_days: int = 365,
        archive_to: str = "archive",
    ) -> dict[str, Any]:
        """Archive events older than the specified number of days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)

        count_stmt = (
            select(func.count())
            .select_from(AuditEvent)
            .where(AuditEvent.timestamp < cutoff)
        )
        total = (await self._session.execute(count_stmt)).scalar() or 0

        if total == 0:
            return {
                "archived": 0,
                "cutoff_date": cutoff.isoformat(),
                "destination": archive_to,
            }

        archived = await self._archive_events(cutoff)

        return {
            "archived": archived,
            "cutoff_date": cutoff.isoformat(),
            "destination": archive_to,
        }

    async def get_retention_stats(self) -> dict[str, Any]:
        """Return statistics about audit event distribution by age."""
        now = datetime.now(timezone.utc)
        buckets = [
            ("last_24h", now - timedelta(hours=24)),
            ("last_7d", now - timedelta(days=7)),
            ("last_30d", now - timedelta(days=30)),
            ("last_90d", now - timedelta(days=90)),
            ("last_365d", now - timedelta(days=365)),
            ("older", None),
        ]

        stats: dict[str, int] = {}
        prev_cutoff = None

        for label, cutoff in reversed(buckets):
            stmt = select(func.count()).select_from(AuditEvent)
            if cutoff:
                stmt = stmt.where(AuditEvent.timestamp >= cutoff)
            if prev_cutoff:
                stmt = stmt.where(AuditEvent.timestamp < prev_cutoff)
            stats[label] = (await self._session.execute(stmt)).scalar() or 0
            prev_cutoff = cutoff

        total_stmt = select(func.count()).select_from(AuditEvent)
        total = (await self._session.execute(total_stmt)).scalar() or 0

        oldest_stmt = (
            select(AuditEvent.timestamp)
            .order_by(AuditEvent.timestamp.asc())
            .limit(1)
        )
        oldest = (await self._session.execute(oldest_stmt)).scalar()

        return {
            "total_events": total,
            "oldest_event": oldest.isoformat() if oldest else None,
            "distribution": stats,
            "policies": dict(self._policies),
        }

    async def _archive_events(self, cutoff: datetime) -> int:
        """Select and archive events before cutoff, then return count.

        In a real system this would push to S3 / cold storage. For now we mark
        events with a special ``details`` field so downstream consumers know
        they were archived.
        """
        stmt = (
            select(AuditEvent)
            .where(AuditEvent.timestamp < cutoff)
            .order_by(AuditEvent.timestamp.asc())
            .limit(1000)
        )
        result = await self._session.execute(stmt)
        events = result.scalars().all()

        count = 0
        for event in events:
            details = event.details or {}
            details["_archived"] = True
            details["_archived_at"] = datetime.now(timezone.utc).isoformat()
            event.details = details
            count += 1

        await self._session.flush()
        return count
