"""MCP tools for audit log querying, integrity verification, and export."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import blake3


_audit_log: list[dict[str, Any]] = []
_chain_hashes: list[str] = []


def _compute_hash(entry: dict[str, Any], previous_hash: str) -> str:
    canonical = json.dumps(entry, sort_keys=True, separators=(",", ":"))
    hasher = blake3.blake3()
    hasher.update(canonical.encode())
    hasher.update(previous_hash.encode())
    return hasher.hexdigest()


def _append_entry(entry: dict[str, Any]) -> str:
    previous_hash = _chain_hashes[-1] if _chain_hashes else "0" * 64
    entry_hash = _compute_hash(entry, previous_hash)
    entry["hash"] = entry_hash
    entry["previous_hash"] = previous_hash
    _audit_log.append(entry)
    _chain_hashes.append(entry_hash)
    return entry_hash


def add_audit_entry(
    event_type: str,
    actor_id: str,
    target_id: str | None = None,
    details: dict[str, Any] | None = None,
    severity: str = "info",
) -> str:
    entry = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "actor_id": actor_id,
        "target_id": target_id,
        "details": details or {},
        "severity": severity,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return _append_entry(entry)


async def query_audit_log(
    event_type: str | None = None,
    actor_id: str | None = None,
    target_id: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    severity: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    results = list(_audit_log)

    if event_type:
        results = [e for e in results if e.get("event_type") == event_type]
    if actor_id:
        results = [e for e in results if e.get("actor_id") == actor_id]
    if target_id:
        results = [e for e in results if e.get("target_id") == target_id]
    if severity:
        results = [e for e in results if e.get("severity") == severity]
    if start_time:
        results = [e for e in results if e.get("timestamp", "") >= start_time]
    if end_time:
        results = [e for e in results if e.get("timestamp", "") <= end_time]

    total = len(results)
    paginated = results[offset:offset + limit]

    return {
        "events": paginated,
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + limit < total,
    }


async def verify_audit_integrity() -> dict[str, Any]:
    errors: list[dict[str, Any]] = []

    if not _audit_log:
        return {
            "valid": True,
            "total_entries": 0,
            "errors": [],
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

    previous_hash = "0" * 64
    for i, entry in enumerate(_audit_log):
        expected_hash = _compute_hash(
            {k: v for k, v in entry.items() if k not in ("hash", "previous_hash")},
            previous_hash,
        )
        if entry.get("hash") != expected_hash:
            errors.append({
                "index": i,
                "event_id": entry.get("event_id"),
                "error": "hash_mismatch",
                "expected": expected_hash,
                "actual": entry.get("hash"),
            })
        if entry.get("previous_hash") != previous_hash:
            errors.append({
                "index": i,
                "event_id": entry.get("event_id"),
                "error": "previous_hash_mismatch",
                "expected": previous_hash,
                "actual": entry.get("previous_hash"),
            })
        previous_hash = entry.get("hash", "")

    chain_valid = len(errors) == 0
    return {
        "valid": chain_valid,
        "total_entries": len(_audit_log),
        "errors": errors,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


async def export_audit_log(
    format: str = "json",
    start_time: str | None = None,
    end_time: str | None = None,
    event_types: list[str] | None = None,
) -> dict[str, Any]:
    results = list(_audit_log)

    if start_time:
        results = [e for e in results if e.get("timestamp", "") >= start_time]
    if end_time:
        results = [e for e in results if e.get("timestamp", "") <= end_time]
    if event_types:
        results = [e for e in results if e.get("event_type") in event_types]

    if format == "json":
        export_data = json.dumps(results, indent=2, default=str)
    elif format == "csv":
        if results:
            headers = list(results[0].keys())
            lines = [",".join(headers)]
            for entry in results:
                vals = [json.dumps(entry.get(h, "")) for h in headers]
                lines.append(",".join(vals))
            export_data = "\n".join(lines)
        else:
            export_data = ""
    else:
        return {"error": f"Unsupported format: {format}"}

    export_hash = blake3.blake3(export_data.encode()).hexdigest()

    return {
        "format": format,
        "record_count": len(results),
        "export_hash": export_hash,
        "data": export_data,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
