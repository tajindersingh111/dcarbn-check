from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.identity import InvitationStatus, UserStatus


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    tenant_slug: str = Field(min_length=2, max_length=100)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime


class CurrentUserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    tenant_id: UUID
    tenant_name: str
    tenant_slug: str
    roles: list[str]
    is_platform_admin: bool


class InvitationCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    role_names: list[str] = Field(min_length=1, max_length=20)


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    email: str
    full_name: str
    status: InvitationStatus
    role_names: list[str]
    expires_at: datetime
    created_at: datetime


class InvitationCreatedResponse(InvitationResponse):
    invitation_token: str


class InvitationAccept(BaseModel):
    token: str = Field(min_length=32)
    password: str = Field(min_length=12, max_length=256)
    password_confirmation: str = Field(min_length=12, max_length=256)

    @model_validator(mode="after")
    def passwords_match(self) -> "InvitationAccept":
        if self.password != self.password_confirmation:
            raise ValueError("Passwords do not match.")
        return self


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    display_name: str
    description: str | None
    is_system: bool
    is_active: bool


class RoleCreate(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{2,99}$")
    display_name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)


class MembershipResponse(BaseModel):
    id: UUID
    user_id: UUID
    tenant_id: UUID
    email: str
    full_name: str
    user_status: UserStatus
    is_active: bool
    roles: list[str]
    joined_at: datetime | None
    last_login_at: datetime | None
    failed_login_count: int
    locked_until: datetime | None


class MembershipListResponse(BaseModel):
    items: list[MembershipResponse]
    total: int
    limit: int
    offset: int


class MembershipRolesUpdate(BaseModel):
    role_names: list[str] = Field(min_length=1, max_length=20)


class MembershipStatusUpdate(BaseModel):
    is_active: bool


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=12, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)
    new_password_confirmation: str = Field(min_length=12, max_length=256)

    @model_validator(mode="after")
    def passwords_match(self) -> "ChangePasswordRequest":
        if self.new_password != self.new_password_confirmation:
            raise ValueError("Passwords do not match.")
        return self


class TenantOnboardingRequest(BaseModel):
    tenant_name: str = Field(min_length=2, max_length=200)
    tenant_slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,98}[a-z0-9]$")
    owner_email: EmailStr
    owner_full_name: str = Field(min_length=1, max_length=200)


class TenantOnboardingResponse(BaseModel):
    tenant_id: UUID
    tenant_name: str
    tenant_slug: str
    owner_email: str
    invitation_token: str
    invitation_expires_at: datetime
