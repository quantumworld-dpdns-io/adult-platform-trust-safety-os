from __future__ import annotations

import json
import time
import uuid
from collections import defaultdict
from typing import Any

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from src.config.settings import settings

logger = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.monotonic()
        request_id = getattr(request.state, "request_id", "unknown")
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            query=str(request.url.query) if request.url.query else None,
            client=request.client.host if request.client else None,
        )
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.monotonic() - start) * 1000
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
                request_id=request_id,
            )
            raise
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            request_id=request_id,
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, requests_per_minute: int | None = None) -> None:
        super().__init__(app)
        self._requests_per_minute = requests_per_minute or settings.rate_limit.per_minute
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._window = 60.0

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = self._get_client_ip(request)
        now = time.monotonic()
        self._buckets[client_ip] = [
            t for t in self._buckets[client_ip] if now - t < self._window
        ]
        if len(self._buckets[client_ip]) >= self._requests_per_minute:
            retry_after = int(self._window - (now - self._buckets[client_ip][0]))
            return JSONResponse(
                status_code=429,
                content={
                    "type": "about:blank",
                    "title": "Rate Limit Exceeded",
                    "status": 429,
                    "detail": f"Rate limit of {self._requests_per_minute} requests per minute exceeded",
                },
                headers={"Retry-After": str(max(retry_after, 1))},
            )
        self._buckets[client_ip].append(now)
        return await call_next(request)


class CORSMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: Any,
        allow_origins: list[str] | None = None,
        allow_methods: list[str] | None = None,
        allow_headers: list[str] | None = None,
        allow_credentials: bool = True,
    ) -> None:
        super().__init__(app)
        self._allow_origins = allow_origins or ["*"]
        self._allow_methods = allow_methods or ["*"]
        self._allow_headers = allow_headers or ["*"]
        self._allow_credentials = allow_credentials

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method == "OPTIONS":
            response = Response(status_code=204)
        else:
            response = await call_next(request)

        origin = request.headers.get("Origin", "*")
        if "*" in self._allow_origins or origin in self._allow_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self._allow_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self._allow_headers)
        if self._allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "86400"
        return response
