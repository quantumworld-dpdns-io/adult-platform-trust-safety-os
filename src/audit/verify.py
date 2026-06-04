"""Audit chain integrity verification."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit.merkle import MerkleTree
from src.audit.models import AuditEvent

logger = structlog.get_logger(__name__)


class AuditVerifier:
    """Verify integrity of audit log chains via Merkle trees and sequential checks."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def verify_chain_integrity(
        self,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict:
        """Verify the full chain of audit events in a time window.

        Returns a dict with ``valid``, ``total_events``, ``broken_links``, and
        ``details`` keys.
        """
        stmt = select(AuditEvent).order_by(AuditEvent.timestamp.asc(), AuditEvent.id.asc())
        if start_time:
            stmt = stmt.where(AuditEvent.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(AuditEvent.timestamp <= end_time)

        result = await self._session.execute(stmt)
        events = list(result.scalars().all())

        if not events:
            return {"valid": True, "total_events": 0, "broken_links": [], "details": "empty log"}

        broken_links: list[dict] = []
        merkle = MerkleTree()
        prev_hash: str | None = None

        for event in events:
            computed_hash = self._compute_event_hash(event)

            if event.integrity_hash and event.integrity_hash != computed_hash:
                broken_links.append(
                    {
                        "event_id": str(event.id),
                        "type": "hash_mismatch",
                        "expected": computed_hash,
                        "actual": event.integrity_hash,
                    }
                )

            event_bytes = json.dumps(
                {
                    "id": str(event.id),
                    "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                    "actor_id": event.actor_id,
                    "action": event.action.value if event.action else None,
                    "resource_type": event.resource_type,
                    "resource_id": event.resource_id,
                },
                sort_keys=True,
            ).encode()
            merkle.add_leaf(event_bytes)
            prev_hash = computed_hash

        merkle.build_tree()

        return {
            "valid": len(broken_links) == 0,
            "total_events": len(events),
            "broken_links": broken_links,
            "merkle_root": merkle.get_root().hex() if merkle.get_root() else None,
            "tree_height": merkle.get_tree_height(),
        }

    async def verify_event(self, event_id: str) -> dict:
        """Verify a single event's integrity hash."""
        from uuid import UUID

        stmt = select(AuditEvent).where(AuditEvent.id == UUID(event_id))
        result = await self._session.execute(stmt)
        event = result.scalar_one_or_none()

        if event is None:
            return {"valid": False, "error": "event_not_found"}

        computed = self._compute_event_hash(event)
        valid = event.integrity_hash == computed

        return {
            "valid": valid,
            "event_id": event_id,
            "stored_hash": event.integrity_hash,
            "computed_hash": computed,
        }

    async def verify_time_window(
        self, window_minutes: int = 60
    ) -> dict:
        """Verify all events within a sliding time window."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(minutes=window_minutes)
        return await self.verify_chain_integrity(start_time=start, end_time=now)

    async def full_verification(self) -> dict:
        """Run all verification checks and produce a comprehensive report."""
        chain_result = await self.verify_chain_integrity()
        total_stmt = select(func.count()).select_from(AuditEvent)
        total = (await self._session.execute(total_stmt)).scalar() or 0

        corrupted_stmt = (
            select(func.count())
            .select_from(AuditEvent)
            .where(AuditEvent.integrity_hash.is_(None))
        )
        missing_hash = (await self._session.execute(corrupted_stmt)).scalar() or 0

        return {
            "chain_integrity": chain_result,
            "total_events": total,
            "events_missing_hash": missing_hash,
            "overall_valid": chain_result["valid"] and missing_hash == 0,
        }

    @staticmethod
    def _compute_event_hash(event: AuditEvent) -> str:
        payload = json.dumps(
            {
                "id": str(event.id),
                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                "actor_id": event.actor_id,
                "actor_type": event.actor_type.value if event.actor_type else None,
                "action": event.action.value if event.action else None,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "details": event.details,
                "ip_address": event.ip_address,
                "user_agent": event.user_agent,
                "session_id": event.session_id,
            },
            sort_keys=True,
            default=str,
        ).encode()
        return hashlib.sha256(payload).hexdigest()
