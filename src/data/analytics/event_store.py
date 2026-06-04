"""Event-sourcing store backed by DuckDB for trust & safety analytics."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from .duckdb_engine import DuckDBEngine


class EventStore:
    """Append-only event store with time-range and type-based queries."""

    _DDL = """
        CREATE TABLE IF NOT EXISTS events (
            event_id   VARCHAR PRIMARY KEY,
            event_type VARCHAR NOT NULL,
            timestamp  TIMESTAMP NOT NULL,
            payload    VARCHAR NOT NULL,
            metadata   VARCHAR DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
        CREATE INDEX IF NOT EXISTS idx_events_ts   ON events(timestamp);
    """

    def __init__(self, engine: DuckDBEngine) -> None:
        """Initialise the store with an existing DuckDB engine.

        Args:
            engine: A :class:`DuckDBEngine` instance (in-memory or on-disk).
        """
        self._engine = engine
        for stmt in self._DDL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                self._engine.execute(stmt)

    # ── Append ─────────────────────────────────────────────────

    def append_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        event_id: str | None = None,
        timestamp: datetime | None = None,
    ) -> str:
        """Write a new event to the store.

        Args:
            event_type: Category / kind of event (e.g. ``"moderation.flag"``).
            payload: Arbitrary JSON-serialisable event payload.
            metadata: Optional sidecar metadata.
            event_id: UUID override (auto-generated when omitted).
            timestamp: Event time (defaults to ``datetime.now(UTC)``).

        Returns:
            The event ID.
        """
        eid = event_id or uuid4().hex
        ts = timestamp or datetime.now(timezone.utc)
        self._engine.insert(
            "events",
            [
                {
                    "event_id": eid,
                    "event_type": event_type,
                    "timestamp": ts,
                    "payload": json.dumps(payload, default=str),
                    "metadata": json.dumps(metadata or {}, default=str),
                }
            ],
        )
        return eid

    # ── Query ──────────────────────────────────────────────────

    def query_events(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Return the most recent events (newest first).

        Args:
            limit: Maximum rows to return.
            offset: Row offset for pagination.
        """
        rows = self._engine.query(
            "SELECT * FROM events ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return self._hydrate(rows)

    def get_events_by_type(
        self,
        event_type: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return events filtered by *event_type*."""
        rows = self._engine.query(
            "SELECT * FROM events WHERE event_type = ? ORDER BY timestamp DESC LIMIT ?",
            (event_type, limit),
        )
        return self._hydrate(rows)

    def get_events_by_time_range(
        self,
        start: datetime,
        end: datetime,
        event_type: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Return events within a time window.

        Args:
            start: Inclusive lower bound.
            end: Inclusive upper bound.
            event_type: Optional type filter.
            limit: Maximum rows.
        """
        if event_type:
            rows = self._engine.query(
                "SELECT * FROM events WHERE event_type = ? AND timestamp BETWEEN ? AND ? "
                "ORDER BY timestamp DESC LIMIT ?",
                (event_type, start, end, limit),
            )
        else:
            rows = self._engine.query(
                "SELECT * FROM events WHERE timestamp BETWEEN ? AND ? "
                "ORDER BY timestamp DESC LIMIT ?",
                (start, end, limit),
            )
        return self._hydrate(rows)

    def aggregate_events(
        self,
        event_type: str | None = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """Return aggregate counts grouped by event_type.

        Returns:
            ``{"total": <int>, "by_type": {"type": <count>, ...}, "first_event": ..., "last_event": ...}``
        """
        conditions: list[str] = []
        params: list[Any] = []
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if start:
            conditions.append("timestamp >= ?")
            params.append(start)
        if end:
            conditions.append("timestamp <= ?")
            params.append(end)

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        rows = self._engine.query(
            f"SELECT event_type, COUNT(*) as cnt FROM events {where} GROUP BY event_type ORDER BY cnt DESC",
            tuple(params),
        )
        by_type = {r["event_type"]: r["cnt"] for r in rows}
        total = sum(by_type.values())

        bounds = self._engine.query(
            f"SELECT MIN(timestamp) as first_event, MAX(timestamp) as last_event FROM events {where}",
            tuple(params),
        )
        bounds_row = bounds[0] if bounds else {}

        return {
            "total": total,
            "by_type": by_type,
            "first_event": bounds_row.get("first_event"),
            "last_event": bounds_row.get("last_event"),
        }

    # ── Internals ──────────────────────────────────────────────

    @staticmethod
    def _hydrate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Parse JSON payload/metadata strings back into dicts."""
        for row in rows:
            row["payload"] = json.loads(row["payload"]) if isinstance(row.get("payload"), str) else row.get("payload")
            row["metadata"] = json.loads(row["metadata"]) if isinstance(row.get("metadata"), str) else row.get("metadata")
        return rows
