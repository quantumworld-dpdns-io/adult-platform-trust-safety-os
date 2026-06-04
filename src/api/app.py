from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.exception_handlers import (
    authentication_error_handler,
    authorization_error_handler,
    audit_integrity_error_handler,
    http_exception_handler,
    not_found_error_handler,
    rate_limit_error_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from src.api.exceptions import (
    AuditIntegrityError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitExceeded,
    ValidationException,
)
from src.api.health import router as health_router
from src.api.metrics import router as metrics_router
from src.api.middleware import CORSMiddleware, RateLimitMiddleware, RequestIDMiddleware, RequestLoggingMiddleware
from src.api.router import router as api_router
from src.config.logging_config import setup_logging
from src.config.settings import settings

logger = structlog.get_logger(__name__)

START_TIME = time.monotonic()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    logger.info("application_starting", version=settings.app_version, env=settings.app_env)

    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

    engine = create_async_engine(
        settings.database.url,
        echo=settings.database.echo,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.max_overflow,
    )
    app.state.db_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    import redis.asyncio as aioredis

    app.state.redis = aioredis.from_url(
        settings.redis.url,
        max_connections=settings.redis.max_connections,
        socket_timeout=settings.redis.socket_timeout,
    )

    yield

    logger.info("application_shutting_down")
    await app.state.redis.aclose()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_development else [],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ValidationException, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(AuthenticationError, authentication_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(AuthorizationError, authorization_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(NotFoundError, not_found_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RateLimitExceeded, rate_limit_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(AuditIntegrityError, audit_integrity_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(api_router)

    @app.get("/", tags=["root"])
    async def root() -> dict:
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs" if settings.is_development else None,
            "health": "/health/live",
        }

    return app
