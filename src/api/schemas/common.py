from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        return self.per_page


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    per_page: int = Field(description="Items per page")
    pages: int = Field(description="Total number of pages")

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        per_page: int,
    ) -> PaginatedResponse[T]:
        pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        return cls(items=items, total=total, page=page, per_page=per_page, pages=pages)


class ErrorResponse(BaseModel):
    type: str = Field(
        default="about:blank",
        description="URI reference identifying the problem type",
    )
    title: str = Field(description="Short human-readable summary of the problem")
    status: int = Field(description="HTTP status code")
    detail: str | None = Field(default=None, description="Human-readable explanation")
    instance: str | None = Field(default=None, description="URI reference to the specific occurrence")
    errors: dict[str, list[str]] | None = Field(
        default=None,
        description="Field-level validation errors",
    )


class HealthCheckItem(BaseModel):
    status: str
    latency_ms: float | None = None
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str = Field(description="Overall health status")
    version: str = Field(description="Application version")
    uptime: float = Field(description="Uptime in seconds")
    checks: dict[str, HealthCheckItem] | None = Field(default=None)


class SuccessResponse(BaseModel):
    success: bool = True
    message: str = ""
    data: dict | None = None
