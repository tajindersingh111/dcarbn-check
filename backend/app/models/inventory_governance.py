from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class RestatementStatus(StrEnum):
    REQUESTED = "requested"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class RestatementTrigger(StrEnum):
    ACQUISITION = "acquisition"
    DIVESTMENT = "divestment"
    OUTSOURCING_INSOURCING = "outsourcing_insourcing"
    ORGANISATIONAL_BOUNDARY_CHANGE = "organisational_boundary_change"
    OPERATIONAL_BOUNDARY_CHANGE = "operational_boundary_change"
    METHODOLOGY_CHANGE = "methodology_change"
    EMISSION_FACTOR_CHANGE = "emission_factor_change"
    MATERIAL_ERROR = "material_error"
    OTHER = "other"


class ReportStatus(StrEnum):
    DRAFT = "draft"
    FINAL = "final"
    SUPERSEDED = "superseded"


class Scope3CategoryDispositionStatus(StrEnum):
    INCLUDED = "included"
    NOT_RELEVANT = "not_relevant"
    EXCLUDED = "excluded"


class Scope3CategoryDisposition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scope_3_category_dispositions"
    __table_args__ = (
        UniqueConstraint(
            "inventory_id",
            "category",
            name="uq_scope_3_disposition_inventory_category",
        ),
        CheckConstraint(
            "category >= 1 AND category <= 15",
            name="scope_3_disposition_category_range",
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    inventory_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inventories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[int] = mapped_column(Integer, nullable=False)
    disposition: Mapped[Scope3CategoryDispositionStatus] = mapped_column(
        Enum(
            Scope3CategoryDispositionStatus,
            name="scope_3_category_disposition_status",
        ),
        nullable=False,
    )
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_reference: Mapped[str | None] = mapped_column(String(1000))
    prepared_by: Mapped[str] = mapped_column(String(200), nullable=False)
    prepared_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    approved_by: Mapped[str | None] = mapped_column(String(200))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InventoryApproval(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "inventory_approvals"
    __table_args__ = (
        UniqueConstraint(
            "inventory_id",
            "version",
            name="uq_inventory_approval_version",
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    inventory_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inventories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    calculation_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("calculation_runs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, name="inventory_approval_status"),
        nullable=False,
        default=ApprovalStatus.PENDING,
        index=True,
    )
    requested_by: Mapped[str] = mapped_column(String(200), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    reviewer_id: Mapped[str | None] = mapped_column(String(200))
    review_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_reason: Mapped[str | None] = mapped_column(Text)
    evidence_complete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    boundary_complete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    factor_lineage_complete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    calculation_complete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    review_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    inventory = relationship("Inventory", back_populates="approvals")
    calculation_run = relationship("CalculationRun")


class InventoryLock(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "inventory_locks"
    __table_args__ = (
        UniqueConstraint("inventory_id", name="uq_inventory_lock_inventory"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    inventory_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inventories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    approval_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inventory_approvals.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    calculation_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("calculation_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    locked_by: Mapped[str] = mapped_column(String(200), nullable=False)
    locked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lock_reason: Mapped[str] = mapped_column(Text, nullable=False)
    lock_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    inventory = relationship("Inventory", back_populates="lock_record")
    approval = relationship("InventoryApproval")
    calculation_run = relationship("CalculationRun")


class InventoryRestatement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "inventory_restatements"
    __table_args__ = (
        CheckConstraint(
            "estimated_impact_percent IS NULL OR estimated_impact_percent >= 0",
            name="inventory_restatement_impact_nonnegative",
        ),
        CheckConstraint(
            "significance_threshold_percent > 0 "
            "AND significance_threshold_percent <= 100",
            name="inventory_restatement_threshold_range",
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_inventory_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inventories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    replacement_inventory_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inventories.id", ondelete="RESTRICT"),
        unique=True,
    )
    status: Mapped[RestatementStatus] = mapped_column(
        Enum(RestatementStatus, name="inventory_restatement_status"),
        nullable=False,
        default=RestatementStatus.REQUESTED,
        index=True,
    )
    requested_by: Mapped[str] = mapped_column(String(200), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(200))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    materiality_assessment: Mapped[str] = mapped_column(Text, nullable=False)
    trigger: Mapped[RestatementTrigger] = mapped_column(
        Enum(RestatementTrigger, name="inventory_restatement_trigger"),
        nullable=False,
        default=RestatementTrigger.OTHER,
        index=True,
    )
    estimated_impact_percent: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    significance_threshold_percent: Mapped[Decimal] = mapped_column(
        Numeric(7, 4),
        nullable=False,
        default=Decimal("5.0"),
    )
    threshold_exceeded: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    qualitative_override: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    qualitative_override_rationale: Mapped[str | None] = mapped_column(Text)
    boundary_change_summary: Mapped[str | None] = mapped_column(Text)
    decision_reason: Mapped[str | None] = mapped_column(Text)
    requested_changes: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    original_inventory = relationship(
        "Inventory",
        foreign_keys=[original_inventory_id],
        back_populates="restatements",
    )
    replacement_inventory = relationship(
        "Inventory",
        foreign_keys=[replacement_inventory_id],
    )


class AuditReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "audit_reports"
    __table_args__ = (
        UniqueConstraint(
            "inventory_id",
            "version",
            name="uq_audit_report_inventory_version",
        ),
        UniqueConstraint(
            "report_sha256",
            name="uq_audit_report_sha256",
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    inventory_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inventories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    calculation_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("calculation_runs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    approval_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inventory_approvals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="audit_report_status"),
        nullable=False,
        default=ReportStatus.DRAFT,
        index=True,
    )
    generated_by: Mapped[str] = mapped_column(String(200), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finalized_by: Mapped[str | None] = mapped_column(String(200))
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    report_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    report_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    superseded_by_report_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("audit_reports.id", ondelete="SET NULL"),
    )

    inventory = relationship("Inventory", back_populates="audit_reports")
    calculation_run = relationship("CalculationRun")
    approval = relationship("InventoryApproval")
