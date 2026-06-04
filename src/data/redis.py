from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class AsyncRedis:
    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        max_connections: int = 50,
        decode_responses: bool = True,
        socket_connect_timeout: float = 5.0,
    ) -> None:
        self._url = url
        self._max_connections = max_connections
        self._decode_responses = decode_responses
        self._socket_connect_timeout = socket_connect_timeout
        self._client: aioredis.Redis | None = None
        self._pubsub_client: aioredis.Redis | None = None

    async def connect(self) -> aioredis.Redis:
        if self._client is not None:
            return self._client

        pool = aioredis.ConnectionPool.from_url(
            self._url,
            max_connections=self._max_connections,
            decode_responses=self._decode_responses,
            socket_connect_timeout=self._socket_connect_timeout,
        )
        self._client = aioredis.Redis(connection_pool=pool)
        self._pubsub_client = aioredis.Redis(connection_pool=pool)

        await self._client.ping()
        logger.info("Connected to Redis at %s", self._url)
        return self._client

    async def get(self, key: str) -> Any:
        if self._client is None:
            await self.connect()
        assert self._client is not None
        value = await self._client.get(key)
        if value and isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value

    async def set(self, key: str, value: Any, ex: int | None = None) -> bool:
        if self._client is None:
            await self.connect()
        assert self._client is not None

        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        return await self._client.set(key, value, ex=ex)

    async def delete(self, *keys: str) -> int:
        if self._client is None:
            await self.connect()
        assert self._client is not None
        return await self._client.delete(*keys)

    async def exists(self, key: str) -> bool:
        if self._client is None:
            await self.connect()
        assert self._client is not None
        return bool(await self._client.exists(key))

    async def expire(self, key: str, seconds: int) -> bool:
        if self._client is None:
            await self.connect()
        assert self._client is not None
        return await self._client.expire(key, seconds)

    async def hget(self, name: str, key: str) -> Any:
        if self._client is None:
            await self.connect()
        assert self._client is not None
        value = await self._client.hget(name, key)
        if value and isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value

    async def hset(self, name: str, key: str, value: Any) -> int:
        if self._client is None:
            await self.connect()
        assert self._client is not None

        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        return await self._client.hset(name, key, value)

    async def lpush(self, key: str, *values: Any) -> int:
        if self._client is None:
            await self.connect()
        assert self._client is not None

        serialized = []
        for v in values:
            if isinstance(v, (dict, list)):
                serialized.append(json.dumps(v))
            else:
                serialized.append(v)

        return await self._client.lpush(key, *serialized)

    async def rpop(self, key: str) -> Any:
        if self._client is None:
            await self.connect()
        assert self._client is not None
        value = await self._client.rpop(key)
        if value and isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value

    async def pubsub_publish(self, channel: str, message: Any) -> int:
        if self._client is None:
            await self.connect()
        assert self._client is not None

        if isinstance(message, (dict, list)):
            message = json.dumps(message)

        return await self._client.publish(channel, message)

    async def pubsub_subscribe(self, channel: str):
        if self._pubsub_client is None:
            await self.connect()
        assert self._pubsub_client is not None

        pubsub = self._pubsub_client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub

    async def health_check(self) -> dict[str, Any]:
        try:
            if self._client is None:
                await self.connect()
            assert self._client is not None

            info = await self._client.info()
            return {
                "status": "healthy",
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "unknown"),
                "redis_version": info.get("redis_version", "unknown"),
            }
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        if self._pubsub_client is not None:
            await self._pubsub_client.aclose()
            self._pubsub_client = None
        logger.info("Redis connection closed")
