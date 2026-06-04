from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = Field(default=None, min_length=3, max_length=64)
    profile: dict | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    age_verified: bool
    risk_score: float
    is_active: bool
    is_banned: bool
    roles: list[str]
    mfa_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    per_page: int
    pages: int


class AgeVerificationRequest(BaseModel):
    method: str = Field(description="Verification method: document, liveness, id_scan")
    document_type: str | None = Field(default=None, description="Type of ID document")
    document_data: str | None = Field(default=None, description="Base64-encoded document data")
    id_image: str | None = Field(default=None, description="Base64-encoded ID image")
    barcode_data: str | None = Field(default=None, description="Barcode data from ID")
    issued_country: str = Field(default="US", description="Country that issued the document")


class AgeVerificationResponse(BaseModel):
    user_id: uuid.UUID
    status: str
    method: str
    verified_at: datetime | None = None
    age_confirmed: bool
    confidence: float
    details: dict
    error: str | None = None


class RiskFactorItem(BaseModel):
    name: str
    score: float
    weight: float
    details: dict
    detected_at: datetime


class RiskScoreResponse(BaseModel):
    user_id: uuid.UUID
    total_score: float
    level: str
    factors: list[RiskFactorItem]
    assessed_at: datetime
    recommendations: list[str]
