from __future__ import annotations

import functools
import hashlib
import json
import logging
import time
from typing import Any, Callable, Awaitable

from src.data.redis import AsyncRedis

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(
        self,
        redis: AsyncRedis,
        prefix: str = "cache",
        default_ttl: int = 300,
    ) -> None:
        self._redis = redis
        self._prefix = prefix
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0

    def _make_key(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    async def get(self, key: str) -> Any | None:
        full_key = self._make_key(key)
        value = await self._redis.get(full_key)
        if value is not None:
            self._hits += 1
            return value
        self._misses += 1
        return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        full_key = self._make_key(key)
        ttl = ttl or self._default_ttl
        return await self._redis.set(full_key, value, ex=ttl)

    async def delete(self, key: str) -> int:
        full_key = self._make_key(key)
        return await self._redis.delete(full_key)

    async def invalidate_pattern(self, pattern: str) -> int:
        if self._redis._client is None:
            await self._redis.connect()
        assert self._redis._client is not None

        full_pattern = self._make_key(pattern)
        keys = []
        async for key in self._redis._client.scan_iter(match=full_pattern):
            keys.append(key)

        if keys:
            return await self._redis.delete(*keys)
        return 0

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[Any]],
        ttl: int | None = None,
    ) -> Any:
        value = await self.get(key)
        if value is not None:
            return value

        value = await factory()
        await self.set(key, value, ttl=ttl)
        return value

    def decorate_function(
        self,
        key_prefix: str,
        ttl: int | None = None,
        key_builder: Callable[..., str] | None = None,
    ) -> Callable:
        def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
            @functools.wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    key_str = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
                    cache_key = hashlib.md5(key_str.encode()).hexdigest()

                full_key = f"{key_prefix}:{cache_key}"
                value = await self.get(full_key)
                if value is not None:
                    return value

                value = await func(*args, **kwargs)
                await self.set(full_key, value, ttl=ttl)
                return value

            wrapper.invalidate = lambda *a, **kw: self.delete(
                f"{key_prefix}:{key_builder(*a, **kw) if key_builder else hashlib.md5(f'{func.__name__}:{a}:{sorted(kw.items())}'.encode()).hexdigest()}"
            )
            return wrapper

        return decorator

    async def get_stats(self) -> dict[str, Any]:
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / max(total, 1),
            "total_requests": total,
            "prefix": self._prefix,
            "default_ttl": self._default_ttl,
        }

    async def flush(self) -> int:
        count = await self.invalidate_pattern("*")
        self._hits = 0
        self._misses = 0
        return count
