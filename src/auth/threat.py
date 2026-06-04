"""Threat detection: brute force, IP reputation, account takeover, lockout."""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

BRUTE_FORCE_THRESHOLD = 5
BRUTE_FORCE_WINDOW = timedelta(minutes=15)
LOCKOUT_DURATION = timedelta(minutes=30)
FAILED_ATTEMPTS_KEY = "threat:failed_attempts:{identifier}"
LOCKOUT_KEY = "threat:lockout:{identifier}"


class ThreatDetector:
    def __init__(self, redis_client: Any | None = None) -> None:
        self._redis = redis_client
        self._local_failed: dict[str, list[float]] = defaultdict(list)
        self._lockouts: dict[str, float] = {}
        self._ip_reputations: dict[str, dict[str, Any]] = {}

    async def check_brute_force(self, identifier: str) -> dict[str, Any]:
        if self._redis:
            return await self._check_brute_force_redis(identifier)
        return self._check_brute_force_local(identifier)

    async def _check_brute_force_redis(self, identifier: str) -> dict[str, Any]:
        key = FAILED_ATTEMPTS_KEY.format(identifier=identifier)
        now = time.time()
        window_start = now - BRUTE_FORCE_WINDOW.total_seconds()
        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.expire(key, int(BRUTE_FORCE_WINDOW.total_seconds()))
        results = await pipe.execute()
        count = results[1]
        return {
            "is_brute_force": count >= BRUTE_FORCE_THRESHOLD,
            "attempts": count,
            "threshold": BRUTE_FORCE_THRESHOLD,
            "window_seconds": int(BRUTE_FORCE_WINDOW.total_seconds()),
        }

    def _check_brute_force_local(self, identifier: str) -> dict[str, Any]:
        now = time.time()
        window_start = now - BRUTE_FORCE_WINDOW.total_seconds()
        attempts = self._local_failed[identifier]
        self._local_failed[identifier] = [t for t in attempts if t > window_start]
        count = len(self._local_failed[identifier])
        return {
            "is_brute_force": count >= BRUTE_FORCE_THRESHOLD,
            "attempts": count,
            "threshold": BRUTE_FORCE_THRESHOLD,
            "window_seconds": int(BRUTE_FORCE_WINDOW.total_seconds()),
        }

    async def increment_failed_attempts(self, identifier: str) -> int:
        if self._redis:
            return await self._increment_failed_redis(identifier)
        return self._increment_failed_local(identifier)

    async def _increment_failed_redis(self, identifier: str) -> int:
        key = FAILED_ATTEMPTS_KEY.format(identifier=identifier)
        now = time.time()
        pipe = self._redis.pipeline()
        pipe.zadd(key, {str(now): now})
        pipe.zremrangebyscore(key, 0, now - BRUTE_FORCE_WINDOW.total_seconds())
        pipe.zcard(key)
        pipe.expire(key, int(BRUTE_FORCE_WINDOW.total_seconds()))
        results = await pipe.execute()
        return results[2]

    def _increment_failed_local(self, identifier: str) -> int:
        now = time.time()
        window_start = now - BRUTE_FORCE_WINDOW.total_seconds()
        self._local_failed[identifier].append(now)
        self._local_failed[identifier] = [
            t for t in self._local_failed[identifier] if t > window_start
        ]
        return len(self._local_failed[identifier])

    async def reset_failed_attempts(self, identifier: str) -> None:
        if self._redis:
            key = FAILED_ATTEMPTS_KEY.format(identifier=identifier)
            await self._redis.delete(key)
        else:
            self._local_failed.pop(identifier, None)

    async def check_ip_reputation(self, ip_address: str) -> dict[str, Any]:
        cached = self._ip_reputations.get(ip_address)
        if cached:
            return cached
        return {
            "ip": ip_address,
            "is_known_bad": False,
            "risk_score": 0.0,
            "categories": [],
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    async def check_account_takeover(
        self,
        user_id: str,
        *,
        current_ip: str,
        current_user_agent: str,
        recent_ips: list[str] | None = None,
        recent_user_agents: list[str] | None = None,
    ) -> dict[str, Any]:
        signals: list[str] = []
        risk_score = 0.0
        if recent_ips and current_ip not in recent_ips:
            signals.append("new_ip")
            risk_score += 0.3
        if recent_user_agents and current_user_agent not in recent_user_agents:
            signals.append("new_user_agent")
            risk_score += 0.2
        failed = await self.check_brute_force(user_id)
        if failed["is_brute_force"]:
            signals.append("brute_force_detected")
            risk_score += 0.4
        return {
            "user_id": user_id,
            "is_suspicious": risk_score >= 0.5,
            "risk_score": min(risk_score, 1.0),
            "signals": signals,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    async def lock_account(self, identifier: str, duration: timedelta | None = None) -> dict[str, Any]:
        lock_duration = duration or LOCKOUT_DURATION
        lockout_until = datetime.now(timezone.utc) + lock_duration
        self._lockouts[identifier] = lockout_until.timestamp()
        return {
            "identifier": identifier,
            "locked_until": lockout_until.isoformat(),
            "duration_seconds": int(lock_duration.total_seconds()),
            "reason": "threat_detection",
        }

    async def check_lockout(self, identifier: str) -> dict[str, Any]:
        lockout_until = self._lockouts.get(identifier)
        if lockout_until is None:
            return {"is_locked": False, "identifier": identifier}
        now = time.time()
        if now >= lockout_until:
            del self._lockouts[identifier]
            return {"is_locked": False, "identifier": identifier}
        remaining = int(lockout_until - now)
        return {
            "is_locked": True,
            "identifier": identifier,
            "remaining_seconds": remaining,
            "locked_until": datetime.fromtimestamp(lockout_until, tz=timezone.utc).isoformat(),
        }
