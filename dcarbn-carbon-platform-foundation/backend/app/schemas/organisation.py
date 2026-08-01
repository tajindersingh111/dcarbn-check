from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrganisationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=250)
    legal_name: str | None = Field(default=None, max_length=250)
    registration_number: str | None = Field(default=None, max_length=100)
    country_code: str = Field(min_length=2, max_length=2)

    @field_validator("country_code")
    @classmethod
    def uppercase_country_code(cls, value: str) -> str:
        return value.upper()


class OrganisationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=250)
    legal_name: str | None = Field(default=None, max_length=250)
    registration_number: str | None = Field(default=None, max_length=100)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    is_active: bool | None = None

    @field_validator("country_code")
    @classmethod
    def uppercase_country_code(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class OrganisationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    legal_name: str | None
    registration_number: str | None
    country_code: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class OrganisationListResponse(BaseModel):
    items: list[OrganisationResponse]
    total: int
    limit: int
    offset: int
