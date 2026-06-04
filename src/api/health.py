from __future__ import annotations

import time
from typing import AsyncGenerator

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.common import HealthCheckItem, HealthResponse
from src.config.settings import settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])

START_TIME = time.monotonic()


async def _check_db(session: AsyncSession) -> HealthCheckItem:
    start = time.monotonic()
    try:
        await session.execute(text("SELECT 1"))
        latency = (time.monotonic() - start) * 1000
        return HealthCheckItem(status="healthy", latency_ms=round(latency, 2))
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return HealthCheckItem(status="unhealthy", latency_ms=round(latency, 2), detail=str(e))


async def _check_redis() -> HealthCheckItem:
    start = time.monotonic()
    try:
        client = aioredis.from_url(settings.redis.url, socket_timeout=5)
        await client.ping()
        await client.aclose()
        latency = (time.monotonic() - start) * 1000
        return HealthCheckItem(status="healthy", latency_ms=round(latency, 2))
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return HealthCheckItem(status="unhealthy", latency_ms=round(latency, 2), detail=str(e))


async def _check_qdrant() -> HealthCheckItem:
    start = time.monotonic()
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.qdrant.url}/healthz")
            resp.raise_for_status()
        latency = (time.monotonic() - start) * 1000
        return HealthCheckItem(status="healthy", latency_ms=round(latency, 2))
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return HealthCheckItem(status="unhealthy", latency_ms=round(latency, 2), detail=str(e))


async def _check_ollama() -> HealthCheckItem:
    start = time.monotonic()
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ollama.base_url}/api/tags")
            resp.raise_for_status()
        latency = (time.monotonic() - start) * 1000
        return HealthCheckItem(status="healthy", latency_ms=round(latency, 2))
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return HealthCheckItem(status="unhealthy", latency_ms=round(latency, 2), detail=str(e))


@router.get("/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        uptime=round(time.monotonic() - START_TIME, 2),
    )


@router.get("/ready", response_model=HealthResponse)
async def readiness(request: Request) -> HealthResponse:
    checks: dict[str, HealthCheckItem] = {}
    if hasattr(request.app.state, "db_session_factory"):
        async with request.app.state.db_session_factory() as sess:
            checks["database"] = await _check_db(sess)
    else:
        checks["database"] = HealthCheckItem(status="unhealthy", detail="Session factory not initialised")

    checks["redis"] = await _check_redis()
    checks["qdrant"] = await _check_qdrant()
    checks["ollama"] = await _check_ollama()

    overall = "ok" if all(c.status == "healthy" for c in checks.values()) else "degraded"
    return HealthResponse(
        status=overall,
        version=settings.app_version,
        uptime=round(time.monotonic() - START_TIME, 2),
        checks=checks,
    )


@router.get("/startup", response_model=HealthResponse)
async def startup() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        uptime=round(time.monotonic() - START_TIME, 2),
    )
