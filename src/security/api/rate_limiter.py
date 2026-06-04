import time
from typing import Dict, Optional, Tuple


class SlidingWindowRateLimiter:
    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._local_store: Dict[str, list] = {}
        self._limits: Dict[str, Dict] = {}
        self._default_limit = 100
        self._default_window = 60

    def configure_limits(self, key: str, max_requests: int, window_seconds: int) -> None:
        self._limits[key] = {
            "max_requests": max_requests,
            "window_seconds": window_seconds,
        }

    def _get_config(self, key: str) -> Tuple[int, int]:
        config = self._limits.get(key, {})
        return (
            config.get("max_requests", self._default_limit),
            config.get("window_seconds", self._default_window),
        )

    def check_rate_limit(self, key: str, identifier: str) -> Dict:
        max_requests, window = self._get_config(key)
        now = time.time()
        window_start = now - window
        store_key = f"rate:{key}:{identifier}"
        if self._redis:
            return self._check_redis(store_key, max_requests, window, now, window_start)
        return self._check_local(store_key, max_requests, window, now, window_start)

    def _check_redis(self, store_key: str, max_requests: int, window: int,
                      now: float, window_start: float) -> Dict:
        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(store_key, 0, window_start)
        pipe.zadd(store_key, {str(now): now})
        pipe.zcard(store_key)
        pipe.expire(store_key, window)
        results = pipe.execute()
        current_count = results[2]
        remaining = max(0, max_requests - current_count)
        return {
            "allowed": current_count <= max_requests,
            "remaining": remaining,
            "total": max_requests,
            "reset_at": now + window,
        }

    def _check_local(self, store_key: str, max_requests: int, window: int,
                      now: float, window_start: float) -> Dict:
        if store_key not in self._local_store:
            self._local_store[store_key] = []
        self._local_store[store_key] = [
            t for t in self._local_store[store_key] if t > window_start
        ]
        self._local_store[store_key].append(now)
        current_count = len(self._local_store[store_key])
        remaining = max(0, max_requests - current_count)
        return {
            "allowed": current_count <= max_requests,
            "remaining": remaining,
            "total": max_requests,
            "reset_at": now + window,
        }

    def get_remaining(self, key: str, identifier: str) -> int:
        max_requests, window = self._get_config(key)
        now = time.time()
        window_start = now - window
        store_key = f"rate:{key}:{identifier}"
        if self._redis:
            self._redis.zremrangebyscore(store_key, 0, window_start)
            count = self._redis.zcard(store_key)
        else:
            if store_key in self._local_store:
                self._local_store[store_key] = [
                    t for t in self._local_store[store_key] if t > window_start
                ]
                count = len(self._local_store[store_key])
            else:
                count = 0
        return max(0, max_requests - count)

    def reset(self, key: str, identifier: str) -> None:
        store_key = f"rate:{key}:{identifier}"
        if self._redis:
            self._redis.delete(store_key)
        else:
            self._local_store.pop(store_key, None)

    def get_usage_stats(self, key: str, identifier: str) -> Dict:
        max_requests, window = self._get_config(key)
        remaining = self.get_remaining(key, identifier)
        return {
            "key": key,
            "identifier": identifier,
            "limit": max_requests,
            "remaining": remaining,
            "used": max_requests - remaining,
            "window": window,
        }
