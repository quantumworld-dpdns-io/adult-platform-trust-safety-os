from __future__ import annotations

from typing import Any

from fastapi import Request, Response
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class ValidationException(HTTPException):
    def __init__(self, detail: str | None = None, errors: dict[str, list[str]] | None = None) -> None:
        super().__init__(status_code=422, detail=detail)
        self.errors = errors


class AuthenticationError(HTTPException):
    def __init__(self, detail: str = "Could not validate credentials") -> None:
        super().__init__(status_code=401, detail=detail)


class AuthorizationError(HTTPException):
    def __init__(self, detail: str = "Not enough permissions") -> None:
        super().__init__(status_code=403, detail=detail)


class NotFoundError(HTTPException):
    def __init__(self, detail: str = "Resource not found") -> None:
        super().__init__(status_code=404, detail=detail)


class RateLimitExceeded(HTTPException):
    def __init__(self, detail: str = "Rate limit exceeded", retry_after: int = 60) -> None:
        super().__init__(status_code=429, detail=detail)
        self.retry_after = retry_after


class AuditIntegrityError(HTTPException):
    def __init__(self, detail: str = "Audit log integrity check failed") -> None:
        super().__init__(status_code=500, detail=detail)
