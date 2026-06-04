"""DuckDB-based analytics engine."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any, Optional

import duckdb  # type: ignore[import-untyped]


class DuckDBEngine:
    """Lightweight wrapper around DuckDB for OLAP queries.

    Supports in-memory databases and persistent file-based databases.
    """

    def __init__(self, database: str = ":memory:") -> None:
        """Open (or create) a DuckDB database.

        Args:
            database: Path to a ``.duckdb`` file, or ``":memory:"`` for a
                transient in-memory database.
        """
        self._database = database
        self._conn: Optional[duckdb.DuckDBPyConnection] = None

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        """Lazy-open the connection on first use."""
        if self._conn is None:
            self._conn = duckdb.connect(self._database)
        return self._conn

    # ── Core operations ────────────────────────────────────────

    def query(self, sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        """Execute a SQL query and return rows as a list of dicts.

        Args:
            sql: SELECT statement.
            params: Optional positional parameters.

        Returns:
            List of row dicts.
        """
        cursor = self.conn.execute(sql, params or ())
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> duckdb.DuckDBPyConnection:
        """Execute a DDL/DML statement (no result rows returned).

        Args:
            sql: Statement to execute.
            params: Optional positional parameters.

        Returns:
            The underlying cursor for chaining.
        """
        return self.conn.execute(sql, params or ())

    def create_table(self, name: str, columns: dict[str, str]) -> None:
        """Create a table from a column-name → DuckDB-type mapping.

        Example::

            engine.create_table("events", {"id": "INTEGER", "ts": "TIMESTAMP"})
        """
        col_defs = ", ".join(f'"{col}" {dtype}' for col, dtype in columns.items())
        self.execute(f'CREATE TABLE IF NOT EXISTS "{name}" ({col_defs})')

    def insert(self, table: str, rows: list[dict[str, Any]]) -> int:
        """Bulk-insert rows into *table*.

        Args:
            table: Target table name.
            rows: List of dicts whose keys match column names.

        Returns:
            Number of rows inserted.
        """
        if not rows:
            return 0
        columns = list(rows[0].keys())
        col_str = ", ".join(f'"{c}"' for c in columns)
        placeholders = ", ".join(["?"] * len(columns))
        stmt = f'INSERT INTO "{table}" ({col_str}) VALUES ({placeholders})'
        data = [tuple(row[c] for c in columns) for row in rows]
        self.conn.executemany(stmt, data)
        return len(data)

    def get_tables(self) -> list[str]:
        """Return a list of table names in the current database."""
        rows = self.query("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'")
        return [r["table_name"] for r in rows]

    def export_csv(self, sql: str, path: Path | str) -> int:
        """Export the result of *sql* to a CSV file.

        Args:
            sql: SELECT statement to export.
            path: Destination file path.

        Returns:
            Number of rows written.
        """
        rows = self.query(sql)
        if not rows:
            Path(path).write_text("")
            return 0
        columns = list(rows[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
        return len(rows)

    # ── Lifecycle ──────────────────────────────────────────────

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "DuckDBEngine":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()
