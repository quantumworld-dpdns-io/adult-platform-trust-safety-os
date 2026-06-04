from __future__ import annotations

import time
import uuid
from typing import Any, AsyncGenerator

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from src.api.exceptions import (
    AuditIntegrityError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitExceeded,
    ValidationException,
)

logger = structlog.get_logger(__name__)

START_TIME = time.monotonic()


def _problem_detail(
    status: int,
    title: str,
    detail: str | None = None,
    instance: str | None = None,
    errors: dict[str, list[str]] | None = None,
    type_uri: str = "about:blank",
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "type": type_uri,
        "title": title,
        "status": status,
    }
    if detail is not None:
        body["detail"] = detail
    if instance is not None:
        body["instance"] = instance
    if errors is not None:
        body["errors"] = errors
    return body


async def validation_exception_handler(request: Request, exc: ValidationException) -> JSONResponse:
    instance = getattr(request.state, "request_id", None)
    logger.warning("validation_error", detail=exc.detail, errors=exc.errors, request_id=instance)
    return JSONResponse(
        status_code=422,
        content=_problem_detail(422, "Validation Error", detail=exc.detail, instance=instance, errors=exc.errors),
    )


async def authentication_error_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    instance = getattr(request.state, "request_id", None)
    logger.warning("authentication_error", detail=exc.detail, request_id=instance)
    return JSONResponse(
        status_code=401,
        content=_problem_detail(401, "Authentication Error", detail=exc.detail, instance=instance),
        headers={"WWW-Authenticate": "Bearer"},
    )


async def authorization_error_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
    instance = getattr(request.state, "request_id", None)
    logger.warning("authorization_error", detail=exc.detail, request_id=instance)
    return JSONResponse(
        status_code=403,
        content=_problem_detail(403, "Authorization Error", detail=exc.detail, instance=instance),
    )


async def not_found_error_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    instance = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=404,
        content=_problem_detail(404, "Not Found", detail=exc.detail, instance=instance),
    )


async def rate_limit_error_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    instance = getattr(request.state, "request_id", None)
    logger.warning("rate_limit_exceeded", detail=exc.detail, request_id=instance)
    return JSONResponse(
        status_code=429,
        content=_problem_detail(429, "Rate Limit Exceeded", detail=exc.detail, instance=instance),
        headers={"Retry-After": str(exc.retry_after)},
    )


async def audit_integrity_error_handler(request: Request, exc: AuditIntegrityError) -> JSONResponse:
    instance = getattr(request.state, "request_id", None)
    logger.error("audit_integrity_error", detail=exc.detail, request_id=instance)
    return JSONResponse(
        status_code=500,
        content=_problem_detail(500, "Audit Integrity Error", detail=exc.detail, instance=instance),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    instance = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=_problem_detail(exc.status_code, "Error", detail=str(exc.detail), instance=instance),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    instance = getattr(request.state, "request_id", None)
    logger.exception("unhandled_exception", exc_info=exc, request_id=instance)
    return JSONResponse(
        status_code=500,
        content=_problem_detail(500, "Internal Server Error", detail="An unexpected error occurred", instance=instance),
    )
