from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ModerationDecisionRequest(BaseModel):
    decision: str = Field(description="Decision: approve, reject, escalate")
    reason: str | None = Field(default=None, description="Reason for the decision")
    notes: str | None = Field(default=None, description="Internal notes")


class ModerationQueueItem(BaseModel):
    id: uuid.UUID
    submitter_id: str
    content_type: str
    raw_content: str | None = None
    metadata: dict | None = None
    status: str
    moderation_score: float | None = None
    created_at: datetime
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    priority: int | None = None
    sla_hours: int | None = None
    overdue: bool = False

    model_config = {"from_attributes": True}


class ModerationStatsResponse(BaseModel):
    pending: int
    in_review: int
    escalated: int
    approved: int
    rejected: int
    total_active: int
    overdue_count: int
    average_resolution_hours: float | None = None


class AppealRequest(BaseModel):
    content_id: uuid.UUID
    reason: str = Field(min_length=10, max_length=2000, description="Reason for appeal")
    evidence_url: str | None = Field(default=None, description="URL to supporting evidence")


class ReportCreate(BaseModel):
    target_content_id: uuid.UUID | None = None
    target_user_id: uuid.UUID | None = None
    reason: str = Field(min_length=1, max_length=128, description="Report reason category")
    description: str | None = Field(default=None, max_length=5000, description="Detailed description")


class ReportResponse(BaseModel):
    id: uuid.UUID
    reporter_id: str
    target_content_id: str | None = None
    target_user_id: str | None = None
    reason: str
    description: str | None = None
    status: str
    created_at: datetime
    resolved_at: datetime | None = None
    resolved_by: str | None = None

    model_config = {"from_attributes": True}
