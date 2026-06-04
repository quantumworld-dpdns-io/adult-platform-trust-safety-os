"""Async audit logger with batched writes."""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Sequence

import structlog
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit.merkle import MerkleTree
from src.audit.models import AuditEvent, ActionType, ActorType
from src.config.settings import settings

logger = structlog.get_logger(__name__)


class AuditLogger:
    """Write audit events to the database with optional batching and Merkle chaining."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._batch: list[dict] = []
        self._lock = asyncio.Lock()
        self._merkle = MerkleTree()
        self._batch_size = settings.audit.batch_size

    async def log_event(
        self,
        *,
        actor_id: str | None,
        actor_type: ActorType,
        action: ActionType,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
    ) -> AuditEvent:
        event_data = {
            "id": uuid.uuid4(),
            "actor_id": actor_id,
            "actor_type": actor_type,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "session_id": session_id,
        }

        integrity_input = json.dumps(
            {k: str(v) for k, v in event_data.items() if v is not None},
            sort_keys=True,
            default=str,
        ).encode()
        integrity_hash = hashlib.sha256(integrity_input).hexdigest()
        event_data["integrity_hash"] = integrity_hash

        event = AuditEvent(**event_data)
        self._session.add(event)

        leaf_idx = self._merkle.add_leaf(integrity_input)
        self._merkle.build_tree()

        batch_record = {**event_data, "merkle_leaf_index": leaf_idx}
        async with self._lock:
            self._batch.append(batch_record)
            if len(self._batch) >= self._batch_size:
                await self._flush()

        await self._session.flush()
        logger.info(
            "audit_event_logged",
            event_id=str(event.id),
            action=action.value,
            actor_type=actor_type.value,
        )
        return event

    async def log_batch(self, events: Sequence[dict]) -> list[AuditEvent]:
        """Log multiple events atomically."""
        created: list[AuditEvent] = []
        for event_kwargs in events:
            event = await self.log_event(**event_kwargs)
            created.append(event)
        return created

    async def get_events(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> Sequence[AuditEvent]:
        stmt = select(AuditEvent).order_by(AuditEvent.timestamp.desc())
        if start_time:
            stmt = stmt.where(AuditEvent.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(AuditEvent.timestamp <= end_time)
        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_events_by_actor(
        self, actor_id: str, *, limit: int = 100
    ) -> Sequence[AuditEvent]:
        stmt = (
            select(AuditEvent)
            .where(AuditEvent.actor_id == actor_id)
            .order_by(AuditEvent.timestamp.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_events_by_resource(
        self, resource_type: str, resource_id: str, *, limit: int = 100
    ) -> Sequence[AuditEvent]:
        stmt = (
            select(AuditEvent)
            .where(
                and_(
                    AuditEvent.resource_type == resource_type,
                    AuditEvent.resource_id == resource_id,
                )
            )
            .order_by(AuditEvent.timestamp.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def _flush(self) -> None:
        if not self._batch:
            return
        batch = self._batch[:]
        self._batch.clear()
        logger.info("audit_batch_flushed", count=len(batch))

    async def flush_batch(self) -> None:
        async with self._lock:
            await self._flush()

    @property
    def merkle_root(self) -> bytes | None:
        return self._merkle.get_root()
