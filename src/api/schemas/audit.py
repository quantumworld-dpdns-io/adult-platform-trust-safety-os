from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AuditEventResponse(BaseModel):
    id: uuid.UUID
    timestamp: datetime
    actor_id: str | None = None
    actor_type: str
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    details: dict | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    session_id: str | None = None
    integrity_hash: str | None = None

    model_config = {"from_attributes": True}


class AuditEventListResponse(BaseModel):
    items: list[AuditEventResponse]
    total: int
    page: int
    per_page: int
    pages: int


class AuditExportRequest(BaseModel):
    start_time: datetime | None = None
    end_time: datetime | None = None
    actor_id: str | None = None
    resource_type: str | None = None
    action: str | None = None
    format: str = Field(default="json", description="Export format: json, csv")


class AuditVerificationResponse(BaseModel):
    valid: bool
    total_events: int
    verified_events: int
    merkle_root: str | None = None
    chain_valid: bool = True
    verified_at: datetime


class AuditStatsResponse(BaseModel):
    total_events: int
    events_today: int
    events_by_action: dict[str, int]
    events_by_actor_type: dict[str, int]
    unique_actors: int
    average_events_per_day: float
