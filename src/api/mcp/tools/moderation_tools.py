"""MCP tools for content moderation actions: approve, reject, escalate, queue."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from src.api.mcp.tools.content_tools import _content_store


_moderation_queue: list[dict[str, Any]] = []
_action_log: list[dict[str, Any]] = []


async def approve_content(
    content_id: str,
    reviewer_id: str,
    reason: str = "Approved by moderator",
) -> dict[str, Any]:
    if content_id not in _content_store:
        return {"error": "Content not found", "content_id": content_id}

    record = _content_store[content_id]
    now = datetime.now(timezone.utc).isoformat()

    record["status"] = "APPROVED"
    record["reviewed_at"] = now
    record["reviewed_by"] = reviewer_id
    record["review_reason"] = reason

    action = {
        "action_id": str(uuid.uuid4()),
        "content_id": content_id,
        "action": "APPROVE",
        "reviewer_id": reviewer_id,
        "reason": reason,
        "timestamp": now,
    }
    _action_log.append(action)

    return {
        "success": True,
        "content_id": content_id,
        "status": "APPROVED",
        "action_id": action["action_id"],
    }


async def reject_content(
    content_id: str,
    reviewer_id: str,
    reason: str = "Rejected by moderator",
    policy_violations: list[str] | None = None,
) -> dict[str, Any]:
    if content_id not in _content_store:
        return {"error": "Content not found", "content_id": content_id}

    record = _content_store[content_id]
    now = datetime.now(timezone.utc).isoformat()

    record["status"] = "REJECTED"
    record["reviewed_at"] = now
    record["reviewed_by"] = reviewer_id
    record["review_reason"] = reason
    record["policy_violations"] = policy_violations or []

    action = {
        "action_id": str(uuid.uuid4()),
        "content_id": content_id,
        "action": "REJECT",
        "reviewer_id": reviewer_id,
        "reason": reason,
        "policy_violations": policy_violations or [],
        "timestamp": now,
    }
    _action_log.append(action)

    return {
        "success": True,
        "content_id": content_id,
        "status": "REJECTED",
        "action_id": action["action_id"],
    }


async def escalate_content(
    content_id: str,
    reviewer_id: str,
    reason: str = "Escalated for senior review",
    severity: str = "medium",
) -> dict[str, Any]:
    if content_id not in _content_store:
        return {"error": "Content not found", "content_id": content_id}

    record = _content_store[content_id]
    now = datetime.now(timezone.utc).isoformat()

    record["status"] = "ESCALATED"
    record["reviewed_at"] = now
    record["reviewed_by"] = reviewer_id
    record["review_reason"] = reason
    record["escalation_severity"] = severity

    _moderation_queue.append({
        "content_id": content_id,
        "priority": {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(severity, 2),
        "queued_at": now,
        "escalated_by": reviewer_id,
    })

    action = {
        "action_id": str(uuid.uuid4()),
        "content_id": content_id,
        "action": "ESCALATE",
        "reviewer_id": reviewer_id,
        "reason": reason,
        "severity": severity,
        "timestamp": now,
    }
    _action_log.append(action)

    return {
        "success": True,
        "content_id": content_id,
        "status": "ESCALATED",
        "action_id": action["action_id"],
        "severity": severity,
    }


async def get_queue(
    status: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    items = []
    for cid, record in _content_store.items():
        item_status = record.get("status", "PENDING")
        if status and item_status != status:
            continue
        items.append({
            "content_id": cid,
            "status": item_status,
            "submitter_id": record.get("submitter_id"),
            "content_type": record.get("content_type"),
            "needs_review": record.get("needs_review"),
            "scanned_at": record.get("scanned_at"),
        })

    items.sort(key=lambda x: x.get("scanned_at", ""), reverse=True)

    return {
        "items": items[:limit],
        "total": len(items),
        "returned": min(len(items), limit),
    }
