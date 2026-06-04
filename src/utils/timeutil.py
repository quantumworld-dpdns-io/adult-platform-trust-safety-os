"""Time and timezone utilities."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional


class TimeUtils:
    """Helpers for UTC timestamps, ISO-8601, relative formatting, and time windows."""

    _UTC = timezone.utc

    # ── Current time ───────────────────────────────────────────

    @classmethod
    def utc_now(cls) -> datetime:
        """Return the current UTC datetime (timezone-aware)."""
        return datetime.now(timezone.utc)

    @classmethod
    def utc_iso(cls) -> str:
        """Return the current UTC time as an ISO-8601 string."""
        return cls.utc_now().isoformat()

    # ── Parsing ────────────────────────────────────────────────

    @staticmethod
    def parse_iso(value: str) -> datetime:
        """Parse an ISO-8601 string into a timezone-aware datetime.

        Handles both ``Z`` suffix and ``+00:00`` offset formats.

        Raises:
            ValueError: If the string cannot be parsed.
        """
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    # ── Conversion ─────────────────────────────────────────────

    @staticmethod
    def to_timestamp(dt: datetime) -> float:
        """Convert a datetime to a POSIX timestamp (seconds since epoch)."""
        return dt.timestamp()

    @classmethod
    def from_timestamp(cls, ts: float) -> datetime:
        """Convert a POSIX timestamp to a timezone-aware UTC datetime."""
        return datetime.fromtimestamp(ts, tz=timezone.utc)

    # ── Formatting ─────────────────────────────────────────────

    @classmethod
    def format_relative_time(
        cls,
        dt: datetime,
        now: Optional[datetime] = None,
    ) -> str:
        """Return a human-friendly relative-time string.

        Examples: ``"just now"``, ``"5 minutes ago"``, ``"3 hours ago"``,
        ``"2 days ago"``, ``"1 month ago"``.
        """
        if now is None:
            now = cls.utc_now()

        diff = now - dt
        seconds = int(diff.total_seconds())

        if seconds < 0:
            return cls._format_future(-seconds)
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            m = seconds // 60
            return f"{m} minute{'s' if m != 1 else ''} ago"
        if seconds < 86400:
            h = seconds // 3600
            return f"{h} hour{'s' if h != 1 else ''} ago"
        if seconds < 2592000:
            d = seconds // 86400
            return f"{d} day{'s' if d != 1 else ''} ago"
        months = seconds // 2592000
        return f"{months} month{'s' if months != 1 else ''} ago"

    @staticmethod
    def _format_future(seconds: int) -> str:
        if seconds < 60:
            return "in a moment"
        if seconds < 3600:
            m = seconds // 60
            return f"in {m} minute{'s' if m != 1 else ''}"
        if seconds < 86400:
            h = seconds // 3600
            return f"in {h} hour{'s' if h != 1 else ''}"
        d = seconds // 86400
        return f"in {d} day{'s' if d != 1 else ''}"

    # ── Time windows ───────────────────────────────────────────

    @classmethod
    def get_time_window(
        cls,
        dt: datetime,
        window_size: timedelta,
    ) -> tuple[datetime, datetime]:
        """Compute the start and end of a fixed time-window that contains *dt*.

        Windows are aligned to UTC epoch (1970-01-01T00:00:00Z).

        Args:
            dt: A datetime to bucket.
            window_size: Duration of each window.

        Returns:
            Tuple of (window_start, window_end).
        """
        ts = dt.timestamp()
        ws = window_size.total_seconds()
        start_ts = (ts // ws) * ws
        end_ts = start_ts + ws
        return (
            datetime.fromtimestamp(start_ts, tz=timezone.utc),
            datetime.fromtimestamp(end_ts, tz=timezone.utc),
        )
