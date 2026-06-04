"""Reporting engine for trust & safety analytics."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .duckdb_engine import DuckDBEngine


@dataclass
class Report:
    """Container for a generated report."""

    title: str
    generated_at: str
    period_start: str
    period_end: str
    summary: dict[str, Any]
    sections: list[dict[str, Any]] = field(default_factory=list)


class ReportingEngine:
    """Generates moderation, user-activity, content, and security reports.

    Each ``generate_*`` method returns a :class:`Report` dataclass.
    """

    def __init__(self, engine: DuckDBEngine) -> None:
        """Initialise with a DuckDB engine (may be in-memory)."""
        self._engine = engine

    # ── Moderation report ──────────────────────────────────────

    def generate_moderation_report(
        self,
        start: datetime,
        end: datetime,
    ) -> Report:
        """Moderation queue activity report.

        Sections:
            * Flagged content count by category
            * Resolution outcomes (approved / rejected / escalated)
            * Average resolution time
        """
        flagged = self._safe_query(
            "SELECT category, COUNT(*) as cnt FROM moderation_flags "
            "WHERE created_at BETWEEN ? AND ? GROUP BY category ORDER BY cnt DESC",
            (start, end),
        )
        resolutions = self._safe_query(
            "SELECT outcome, COUNT(*) as cnt FROM moderation_actions "
            "WHERE created_at BETWEEN ? AND ? GROUP BY outcome ORDER BY cnt DESC",
            (start, end),
        )
        avg_time = self._safe_query(
            "SELECT AVG(EXTRACT(EPOCH FROM (resolved_at - created_at))) as avg_seconds "
            "FROM moderation_actions WHERE resolved_at IS NOT NULL "
            "AND created_at BETWEEN ? AND ?",
            (start, end),
        )

        return Report(
            title="Moderation Activity Report",
            generated_at=datetime.now(timezone.utc).isoformat(),
            period_start=start.isoformat(),
            period_end=end.isoformat(),
            summary={
                "total_flagged": sum(r["cnt"] for r in flagged),
                "total_resolved": sum(r["cnt"] for r in resolutions),
                "avg_resolution_seconds": avg_time[0]["avg_seconds"] if avg_time else None,
            },
            sections=[
                {"name": "Flags by Category", "rows": flagged},
                {"name": "Resolution Outcomes", "rows": resolutions},
            ],
        )

    # ── User activity report ───────────────────────────────────

    def generate_user_activity_report(
        self,
        start: datetime,
        end: datetime,
    ) -> Report:
        """User sign-ups, logins, and bans during the reporting window."""
        signups = self._safe_query(
            "SELECT DATE_TRUNC('day', created_at) as day, COUNT(*) as cnt "
            "FROM users WHERE created_at BETWEEN ? AND ? GROUP BY day ORDER BY day",
            (start, end),
        )
        logins = self._safe_query(
            "SELECT DATE_TRUNC('day', created_at) as day, COUNT(*) as cnt "
            "FROM login_events WHERE created_at BETWEEN ? AND ? GROUP BY day ORDER BY day",
            (start, end),
        )
        bans = self._safe_query(
            "SELECT reason, COUNT(*) as cnt FROM user_bans "
            "WHERE created_at BETWEEN ? AND ? GROUP BY reason ORDER BY cnt DESC",
            (start, end),
        )

        return Report(
            title="User Activity Report",
            generated_at=datetime.now(timezone.utc).isoformat(),
            period_start=start.isoformat(),
            period_end=end.isoformat(),
            summary={
                "total_signups": sum(r["cnt"] for r in signups),
                "total_logins": sum(r["cnt"] for r in logins),
                "total_bans": sum(r["cnt"] for r in bans),
            },
            sections=[
                {"name": "Daily Sign-ups", "rows": signups},
                {"name": "Daily Logins", "rows": logins},
                {"name": "Bans by Reason", "rows": bans},
            ],
        )

    # ── Content report ─────────────────────────────────────────

    def generate_content_report(
        self,
        start: datetime,
        end: datetime,
    ) -> Report:
        """Content upload, removal, and classification summary."""
        uploads = self._safe_query(
            "SELECT content_type, COUNT(*) as cnt, SUM(file_size_bytes) as total_bytes "
            "FROM content_uploads WHERE created_at BETWEEN ? AND ? "
            "GROUP BY content_type ORDER BY cnt DESC",
            (start, end),
        )
        removals = self._safe_query(
            "SELECT reason, COUNT(*) as cnt FROM content_removals "
            "WHERE created_at BETWEEN ? AND ? GROUP BY reason ORDER BY cnt DESC",
            (start, end),
        )
        classifications = self._safe_query(
            "SELECT classification, COUNT(*) as cnt FROM content_classifications "
            "WHERE created_at BETWEEN ? AND ? GROUP BY classification ORDER BY cnt DESC",
            (start, end),
        )

        return Report(
            title="Content Report",
            generated_at=datetime.now(timezone.utc).isoformat(),
            period_start=start.isoformat(),
            period_end=end.isoformat(),
            summary={
                "total_uploads": sum(r["cnt"] for r in uploads),
                "total_removals": sum(r["cnt"] for r in removals),
                "total_classified": sum(r["cnt"] for r in classifications),
            },
            sections=[
                {"name": "Uploads by Type", "rows": uploads},
                {"name": "Removals by Reason", "rows": removals},
                {"name": "Classifications", "rows": classifications},
            ],
        )

    # ── Security report ────────────────────────────────────────

    def generate_security_report(
        self,
        start: datetime,
        end: datetime,
    ) -> Report:
        """Security incidents: failed logins, rate-limit hits, suspicious activity."""
        failed_logins = self._safe_query(
            "SELECT user_id, COUNT(*) as cnt FROM login_events "
            "WHERE success = false AND created_at BETWEEN ? AND ? "
            "GROUP BY user_id ORDER BY cnt DESC LIMIT 50",
            (start, end),
        )
        rate_limit_hits = self._safe_query(
            "SELECT endpoint, COUNT(*) as cnt FROM rate_limit_events "
            "WHERE created_at BETWEEN ? AND ? GROUP BY endpoint ORDER BY cnt DESC",
            (start, end),
        )
        suspicious = self._safe_query(
            "SELECT event_type, COUNT(*) as cnt FROM security_events "
            "WHERE created_at BETWEEN ? AND ? GROUP BY event_type ORDER BY cnt DESC",
            (start, end),
        )

        return Report(
            title="Security Report",
            generated_at=datetime.now(timezone.utc).isoformat(),
            period_start=start.isoformat(),
            period_end=end.isoformat(),
            summary={
                "total_failed_logins": sum(r["cnt"] for r in failed_logins),
                "total_rate_limit_hits": sum(r["cnt"] for r in rate_limit_hits),
                "total_suspicious_events": sum(r["cnt"] for r in suspicious),
            },
            sections=[
                {"name": "Failed Logins by User", "rows": failed_logins},
                {"name": "Rate-Limit Hits by Endpoint", "rows": rate_limit_hits},
                {"name": "Suspicious Events", "rows": suspicious},
            ],
        )

    # ── Internals ──────────────────────────────────────────────

    def _safe_query(self, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        """Run a query and return [] on error (tables may not exist yet)."""
        try:
            return self._engine.query(sql, params)
        except Exception:
            return []
