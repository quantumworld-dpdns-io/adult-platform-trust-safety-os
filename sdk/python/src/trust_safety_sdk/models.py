"""SDK data models for API requests and responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ContentClassification(BaseModel):
    """Response model for content scanning/classification."""

    content_id: str
    content_type: str
    status: str
    moderation_score: float | None = None
    metadata: dict[str, Any] | None = None


class AgeVerification(BaseModel):
    """Response model for age verification via ZKP."""

    valid: bool
    proof_type: str = "age_over"
    minimum_age: int = 18
    verified_at: str | None = None


class AuditEntry(BaseModel):
    """Model for an audit log entry."""

    id: str
    actor_id: str | None = None
    actor_type: str
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    timestamp: str
    integrity_hash: str | None = None


class ZKPProof(BaseModel):
    """Response model for ZKP verification."""

    valid: bool
    proof_type: str
    metadata: dict[str, Any] | None = None


class AuthTokens(BaseModel):
    """Authentication token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ContentSubmission(BaseModel):
    """Request model for content submission."""

    content_type: str
    raw_content: str
    metadata: dict[str, Any] | None = None


class ModerationDecision(BaseModel):
    """Moderation decision on content."""

    content_id: str
    decision: str  # approved, rejected, escalated
    moderator_id: str | None = None
    reason: str | None = None
    score: float | None = None


class AuditQuery(BaseModel):
    """Query parameters for audit log retrieval."""

    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    actor_id: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    start_time: str | None = None
    end_time: str | None = None
