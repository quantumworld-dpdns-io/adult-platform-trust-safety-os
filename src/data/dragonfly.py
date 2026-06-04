from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class DragonflyStore:
    def __init__(
        self,
        url: str = "redis://localhost:6379/1",
        max_connections: int = 50,
        decode_responses: bool = True,
    ) -> None:
        self._url = url
        self._max_connections = max_connections
        self._decode_responses = decode_responses
        self._client: aioredis.Redis | None = None
        self._cluster_info: dict[str, Any] | None = None

    async def connect(self) -> aioredis.Redis:
        if self._client is not None:
            return self._client

        pool = aioredis.ConnectionPool.from_url(
            self._url,
            max_connections=self._max_connections,
            decode_responses=self._decode_responses,
        )
        self._client = aioredis.Redis(connection_pool=pool)
        await self._client.ping()
        logger.info("Connected to DragonflyDB at %s", self._url)
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
        serialized = [json.dumps(v) if isinstance(v, (dict, list)) else v for v in values]
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
        if self._client is None:
            await self.connect()
        assert self._client is not None
        pubsub = self._client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub

    async def memtier_benchmark(
        self,
        clients: int = 50,
        threads: int = 4,
        requests: int = 10000,
        data_size: int = 32,
    ) -> dict[str, Any]:
        if self._client is None:
            await self.connect()
        assert self._client is not None

        try:
            import subprocess

            cmd = [
                "memtier_benchmark",
                "-s", self._url.replace("redis://", ""),
                "-c", str(clients),
                "-t", str(threads),
                "-n", str(requests),
                "-d", str(data_size),
                "--json-out=-",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                return json.loads(result.stdout) if result.stdout else {"error": "empty output"}
            return {"error": result.stderr, "returncode": result.returncode}
        except FileNotFoundError:
            return {"error": "memtier_benchmark not installed"}
        except subprocess.TimeoutExpired:
            return {"error": "benchmark timed out"}
        except Exception as exc:
            return {"error": str(exc)}

    async def cluster_info(self) -> dict[str, Any]:
        if self._client is None:
            await self.connect()
        assert self._client is not None

        try:
            info = await self._client.info()
            server_info = await self._client.info("server")
            memory_info = await self._client.info("memory")
            stats_info = await self._client.info("stats")

            self._cluster_info = {
                "server": {
                    "redis_version": server_info.get("redis_version", "unknown"),
                    "dragonfly_version": server_info.get("dragonfly_version", "unknown"),
                    "uptime_in_seconds": server_info.get("uptime_in_seconds", 0),
                    "tcp_port": server_info.get("tcp_port", 6379),
                },
                "memory": {
                    "used_memory": memory_info.get("used_memory", 0),
                    "used_memory_human": memory_info.get("used_memory_human", "unknown"),
                    "max_memory": memory_info.get("maxmemory", 0),
                    "max_memory_human": memory_info.get("maxmemory_human", "unknown"),
                    "mem_fragmentation_ratio": memory_info.get("mem_fragmentation_ratio", 0),
                },
                "stats": {
                    "total_connections_received": stats_info.get("total_connections_received", 0),
                    "total_commands_processed": stats_info.get("total_commands_processed", 0),
                    "instantaneous_ops_per_sec": stats_info.get("instantaneous_ops_per_sec", 0),
                    "keyspace_hits": stats_info.get("keyspace_hits", 0),
                    "keyspace_misses": stats_info.get("keyspace_misses", 0),
                    "hit_rate": (
                        stats_info.get("keyspace_hits", 0)
                        / max(stats_info.get("keyspace_hits", 0) + stats_info.get("keyspace_misses", 0), 1)
                    ),
                },
                "clients": {
                    "connected_clients": info.get("connected_clients", 0),
                    "blocked_clients": info.get("blocked_clients", 0),
                },
            }
            return self._cluster_info
        except Exception as exc:
            return {"error": str(exc)}

    async def get_memory_usage(self, key: str) -> dict[str, Any]:
        if self._client is None:
            await self.connect()
        assert self._client is not None

        try:
            memory = await self._client.memory_usage(key)
            ttl = await self._client.ttl(key)
            return {
                "key": key,
                "memory_bytes": memory,
                "ttl_seconds": ttl,
            }
        except Exception as exc:
            return {"key": key, "error": str(exc)}

    async def health_check(self) -> dict[str, Any]:
        try:
            if self._client is None:
                await self.connect()
            assert self._client is not None

            await self._client.ping()
            info = await self._client.info("server")
            return {
                "status": "healthy",
                "version": info.get("redis_version", info.get("dragonfly_version", "unknown")),
                "url": self._url,
            }
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        logger.info("DragonflyDB connection closed")
