from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.security import SecurityEventSeverity


class CookieSessionResponse(BaseModel):
    authenticated: bool = True
    requires_mfa: bool = False
    mfa_challenge_token: str | None = None
    access_token_expires_at: datetime | None = None


class MfaVerifyLoginRequest(BaseModel):
    challenge_token: str = Field(min_length=32)
    code: str = Field(min_length=6, max_length=32)


class MfaEnrollmentStartResponse(BaseModel):
    secret: str
    provisioning_uri: str


class MfaEnrollmentConfirmRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class MfaEnrollmentConfirmResponse(BaseModel):
    recovery_codes: list[str]


class MfaDisableRequest(BaseModel):
    password: str = Field(min_length=12, max_length=256)
    code: str = Field(min_length=6, max_length=32)


class PasswordResetRequest(BaseModel):
    email: EmailStr
    tenant_slug: str = Field(min_length=2, max_length=100)


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=32)
    password: str = Field(min_length=12, max_length=256)
    password_confirmation: str = Field(min_length=12, max_length=256)

    @model_validator(mode="after")
    def validate_passwords(self) -> "PasswordResetConfirm":
        if self.password != self.password_confirmation:
            raise ValueError("Passwords do not match.")
        return self


class SecurityEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID | None
    user_id: UUID | None
    event_type: str
    severity: SecurityEventSeverity
    success: bool
    ip_address: str | None
    user_agent: str | None
    correlation_id: str | None
    description: str
    event_data: dict[str, object]
    occurred_at: datetime


class SecurityEventListResponse(BaseModel):
    items: list[SecurityEventResponse]
    total: int
    limit: int
    offset: int
