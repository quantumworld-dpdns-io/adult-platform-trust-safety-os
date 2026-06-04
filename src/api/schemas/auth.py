from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    mfa_code: str | None = Field(default=None, description="MFA TOTP code if enabled")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class MFAEnableResponse(BaseModel):
    secret: str
    provisioning_uri: str
    backup_codes: list[str]


class MFAVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6, description="6-digit TOTP code")


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
