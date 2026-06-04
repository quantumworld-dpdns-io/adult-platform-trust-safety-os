from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ContentCreate(BaseModel):
    content_type: str = Field(description="Content type: TEXT, IMAGE, VIDEO, AUDIO, LIVE_STREAM")
    raw_content: str | None = Field(default=None, description="Text content or description")
    metadata: dict | None = Field(default=None, description="Additional metadata")


class ContentResponse(BaseModel):
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

    model_config = {"from_attributes": True}


class ContentListResponse(BaseModel):
    items: list[ContentResponse]
    total: int
    page: int
    per_page: int
    pages: int


class ContentClassificationResponse(BaseModel):
    content_id: uuid.UUID
    classifications: list[ClassificationItem]
    overall_score: float
    flagged: bool
    categories: list[str]
    processed_at: datetime


class ClassificationItem(BaseModel):
    category: str
    score: float
    threshold: float
    flagged: bool


class ModerationStatusResponse(BaseModel):
    content_id: uuid.UUID
    status: str
    moderation_score: float | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    queue_priority: int | None = None
    sla_deadline: datetime | None = None
