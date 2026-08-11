from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.workload import WorkloadStatus, WorkloadType


class MethodologyDualRunCreate(BaseModel):
    governed_method_id: str = Field(min_length=1, max_length=250)
    methodology_pack_id: UUID
    emission_factor_id: UUID
    activity_value: Decimal = Field(ge=0)
    allocation_percentage: Decimal = Field(ge=0, le=100)
    source_reference: str = Field(min_length=1, max_length=200)
    inventory_id: UUID | None = None


class WorkloadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    organisation_id: UUID | None
    inventory_id: UUID | None
    workload_type: WorkloadType
    status: WorkloadStatus
    requested_by: str
    priority: int
    attempts: int
    max_attempts: int
    scheduled_at: datetime
    lease_expires_at: datetime | None
    heartbeat_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    progress_current: int
    progress_total: int | None
    error_code: str | None
    error_message: str | None
    result_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class WorkloadListResponse(BaseModel):
    items: list[WorkloadResponse]
    next_cursor: str | None = None


class WorkloadQueueSnapshotResponse(BaseModel):
    counts_by_status: dict[str, int]
    oldest_queued_age_seconds: float
