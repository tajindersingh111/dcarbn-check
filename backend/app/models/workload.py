from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class WorkloadType(StrEnum):
    CALCULATION = "calculation"
    DATA_IMPORT = "data_import"
    REPORT_EXPORT = "report_export"
    CONNECTOR_SYNC = "connector_sync"


class WorkloadStatus(StrEnum):
    QUEUED = "queued"
    LEASED = "leased"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEAD_LETTERED = "dead_lettered"


class DurableWorkload(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persisted tenant-scoped work item; the database is the delivery authority."""

    __tablename__ = "durable_workloads"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_workload_tenant_idempotency"),
        CheckConstraint("attempts >= 0", name="workload_attempts_non_negative"),
        CheckConstraint("max_attempts > 0", name="workload_max_attempts_positive"),
        CheckConstraint("progress_current >= 0", name="workload_progress_non_negative"),
        Index("ix_workload_claim", "status", "scheduled_at", "priority", "created_at"),
        Index("ix_workload_tenant_status", "tenant_id", "status", "created_at"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organisation_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        index=True,
    )
    inventory_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inventories.id", ondelete="CASCADE"),
        index=True,
    )
    workload_type: Mapped[WorkloadType] = mapped_column(
        Enum(WorkloadType, name="durable_workload_type"),
        nullable=False,
        index=True,
    )
    status: Mapped[WorkloadStatus] = mapped_column(
        Enum(WorkloadStatus, name="durable_workload_status"),
        nullable=False,
        default=WorkloadStatus.QUEUED,
        index=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(200), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lease_owner: Mapped[str | None] = mapped_column(String(200))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    progress_current: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_total: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    cancelled_by: Mapped[str | None] = mapped_column(String(200))
