from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


@dataclass
class BatchRequest:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    payload: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    created_at: float = field(default_factory=time.time)
    result: Any = None
    error: str | None = None
    status: str = "pending"


@dataclass
class BatchStats:
    total_processed: int = 0
    total_failed: int = 0
    total_batches: int = 0
    avg_batch_size: float = 0.0
    avg_processing_time_ms: float = 0.0
    current_queue_size: int = 0


class BatchProcessor:
    def __init__(
        self,
        process_fn: Callable[[list[dict[str, Any]]], Awaitable[list[Any]]] | None = None,
        batch_size: int = 32,
        max_wait_ms: float = 100.0,
        max_concurrent_batches: int = 4,
    ) -> None:
        self._process_fn = process_fn
        self._batch_size = batch_size
        self._max_wait_ms = max_wait_ms
        self._max_concurrent_batches = max_concurrent_batches
        self._queue: list[BatchRequest] = []
        self._processing = False
        self._semaphore = asyncio.Semaphore(max_concurrent_batches)
        self._stats = BatchStats()
        self._processing_times: list[float] = []

    async def add_request(
        self,
        payload: dict[str, Any],
        priority: int = 0,
    ) -> BatchRequest:
        request = BatchRequest(payload=payload, priority=priority)
        self._queue.append(request)
        self._stats.current_queue_size = len(self._queue)

        self._queue.sort(key=lambda r: r.priority, reverse=True)

        if len(self._queue) >= self._batch_size and not self._processing:
            asyncio.create_task(self._process_queue())

        return request

    async def _process_queue(self) -> None:
        if self._processing:
            return

        self._processing = True
        try:
            while self._queue:
                batch = self._queue[: self._batch_size]
                self._queue = self._queue[self._batch_size :]
                self._stats.current_queue_size = len(self._queue)

                if batch:
                    await self._process_batch_internal(batch)
        finally:
            self._processing = False

    async def process_batch(self) -> list[BatchRequest]:
        if not self._queue:
            return []

        batch = self._queue[: self._batch_size]
        self._queue = self._queue[self._batch_size :]
        self._stats.current_queue_size = len(self._queue)

        return await self._process_batch_internal(batch)

    async def _process_batch_internal(self, batch: list[BatchRequest]) -> list[BatchRequest]:
        async with self._semaphore:
            start_time = time.time()
            self._stats.total_batches += 1

            payloads = [r.payload for r in batch]

            if self._process_fn is not None:
                try:
                    results = await self._process_fn(payloads)
                    for request, result in zip(batch, results, strict=False):
                        request.result = result
                        request.status = "completed"
                        self._stats.total_processed += 1
                except Exception as exc:
                    logger.error("Batch processing failed: %s", exc)
                    for request in batch:
                        request.error = str(exc)
                        request.status = "failed"
                        self._stats.total_failed += 1
            else:
                for request in batch:
                    request.result = {"processed": True, "payload": request.payload}
                    request.status = "completed"
                    self._stats.total_processed += 1

            elapsed_ms = (time.time() - start_time) * 1000
            self._processing_times.append(elapsed_ms)
            if len(self._processing_times) > 100:
                self._processing_times = self._processing_times[-100:]

            self._stats.avg_batch_size = (
                self._stats.total_processed / max(self._stats.total_batches, 1)
            )
            self._stats.avg_processing_time_ms = (
                sum(self._processing_times) / len(self._processing_times)
            )

            return batch

    def get_stats(self) -> BatchStats:
        self._stats.current_queue_size = len(self._queue)
        return self._stats

    def configure_batch_size(self, batch_size: int) -> None:
        self._batch_size = max(1, batch_size)

    def configure_max_wait(self, max_wait_ms: float) -> None:
        self._max_wait_ms = max(1.0, max_wait_ms)

    def configure_concurrent_batches(self, max_concurrent: int) -> None:
        self._max_concurrent_batches = max(1, max_concurrent)
        self._semaphore = asyncio.Semaphore(max_concurrent)

    def get_queue(self) -> list[dict[str, Any]]:
        return [
            {"id": r.id, "status": r.status, "priority": r.priority, "created_at": r.created_at}
            for r in self._queue
        ]

    def get_request(self, request_id: str) -> BatchRequest | None:
        for r in self._queue:
            if r.id == request_id:
                return r
        return None

    def clear_queue(self) -> int:
        count = len(self._queue)
        self._queue.clear()
        self._stats.current_queue_size = 0
        return count
