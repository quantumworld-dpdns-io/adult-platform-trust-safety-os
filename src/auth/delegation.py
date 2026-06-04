"""Token delegation for moderator impersonation with full audit trail."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

DELEGATION_TTL = timedelta(hours=4)
MAX_CONCURRENT_DELEGATIONS = 5


class DelegationAuditEntry:
    def __init__(
        self,
        *,
        action: str,
        delegation_id: str,
        delegator_id: str,
        delegatee_id: str,
        reason: str | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        self.action = action
        self.delegation_id = delegation_id
        self.delegator_id = delegator_id
        self.delegatee_id = delegatee_id
        self.reason = reason
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "delegation_id": self.delegation_id,
            "delegator_id": self.delegator_id,
            "delegatee_id": self.delegatee_id,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }


class DelegationManager:
    def __init__(self) -> None:
        self._delegations: dict[str, dict[str, Any]] = {}
        self._audit_log: list[DelegationAuditEntry] = []

    def create_delegation_token(
        self,
        *,
        delegator_id: str,
        delegatee_id: str,
        reason: str,
        scope: list[str] | None = None,
        expires_in: timedelta | None = None,
    ) -> dict[str, Any]:
        delegation_id = str(uuid.uuid4())
        token = secrets.token_urlsafe(48)
        now = datetime.now(timezone.utc)
        ttl = expires_in or DELEGATION_TTL

        active_count = sum(
            1
            for d in self._delegations.values()
            if d["delegator_id"] == delegator_id and d["is_active"]
        )
        if active_count >= MAX_CONCURRENT_DELEGATIONS:
            raise ValueError(
                f"Maximum concurrent delegations ({MAX_CONCURRENT_DELEGATIONS}) reached"
            )

        delegation: dict[str, Any] = {
            "delegation_id": delegation_id,
            "token": token,
            "token_hash": secrets.token_hex(32),
            "delegator_id": delegator_id,
            "delegatee_id": delegatee_id,
            "reason": reason,
            "scope": scope or ["moderation"],
            "created_at": now.isoformat(),
            "expires_at": (now + ttl).isoformat(),
            "is_active": True,
            "revoked_at": None,
        }
        self._delegations[delegation_id] = delegation

        self._audit(DelegationAuditEntry(
            action="delegation_created",
            delegation_id=delegation_id,
            delegator_id=delegator_id,
            delegatee_id=delegatee_id,
            reason=reason,
        ))

        return delegation

    def verify_delegation(self, delegation_id: str) -> dict[str, Any]:
        delegation = self._delegations.get(delegation_id)
        if delegation is None:
            return {"is_valid": False, "reason": "not_found"}
        if not delegation["is_active"]:
            return {"is_valid": False, "reason": "revoked"}
        expires_at = datetime.fromisoformat(delegation["expires_at"])
        if expires_at < datetime.now(timezone.utc):
            delegation["is_active"] = False
            return {"is_valid": False, "reason": "expired"}
        return {"is_valid": True, "delegation": delegation}

    def list_delegations(
        self,
        *,
        delegator_id: str | None = None,
        delegatee_id: str | None = None,
        include_revoked: bool = False,
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for delegation in self._delegations.values():
            if delegator_id and delegation["delegator_id"] != delegator_id:
                continue
            if delegatee_id and delegation["delegatee_id"] != delegatee_id:
                continue
            if not include_revoked and not delegation["is_active"]:
                continue
            result.append(delegation)
        return result

    def revoke_delegation(
        self,
        delegation_id: str,
        *,
        revoked_by: str | None = None,
        reason: str | None = None,
    ) -> bool:
        delegation = self._delegations.get(delegation_id)
        if delegation is None or not delegation["is_active"]:
            return False
        delegation["is_active"] = False
        delegation["revoked_at"] = datetime.now(timezone.utc).isoformat()

        self._audit(DelegationAuditEntry(
            action="delegation_revoked",
            delegation_id=delegation_id,
            delegator_id=delegation["delegator_id"],
            delegatee_id=delegation["delegatee_id"],
            reason=reason or "revoked",
        ))
        return True

    def get_audit_log(
        self,
        *,
        delegator_id: str | None = None,
        delegatee_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        entries = self._audit_log
        if delegator_id:
            entries = [e for e in entries if e.delegator_id == delegator_id]
        if delegatee_id:
            entries = [e for e in entries if e.delegatee_id == delegatee_id]
        return [e.to_dict() for e in entries[-limit:]]

    def _audit(self, entry: DelegationAuditEntry) -> None:
        self._audit_log.append(entry)
