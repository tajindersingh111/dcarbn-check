from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class InventoryStatus(StrEnum):
    DRAFT = "draft"
    DATA_COLLECTION = "data_collection"
    VALIDATION_REQUIRED = "validation_required"
    READY_FOR_CALCULATION = "ready_for_calculation"
    CALCULATING = "calculating"
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"
    LOCKED = "locked"
    CALCULATION_FAILED = "calculation_failed"
    RESTATEMENT_REQUIRED = "restatement_required"
    SUPERSEDED = "superseded"


class ReportingPeriod(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reporting_periods"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="reporting_period_dates"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organisation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_base_year: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    organisation = relationship("Organisation", back_populates="reporting_periods")
    inventories = relationship(
        "Inventory",
        back_populates="reporting_period",
        cascade="all, delete-orphan",
    )
    organisational_boundaries = relationship(
        "OrganisationalBoundary",
        back_populates="reporting_period",
        cascade="all, delete-orphan",
    )


class Inventory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "inventories"

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reporting_period_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("reporting_periods.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[InventoryStatus] = mapped_column(
        Enum(InventoryStatus, name="inventory_status"),
        nullable=False,
        default=InventoryStatus.DRAFT,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    reporting_period = relationship("ReportingPeriod", back_populates="inventories")
    activities = relationship(
        "ActivityRecord",
        back_populates="inventory",
        cascade="all, delete-orphan",
    )
    calculation_runs = relationship(
        "CalculationRun",
        back_populates="inventory",
        cascade="all, delete-orphan",
    )
    approvals = relationship(
        "InventoryApproval",
        back_populates="inventory",
        cascade="all, delete-orphan",
    )
    lock_record = relationship(
        "InventoryLock",
        back_populates="inventory",
        uselist=False,
    )
    restatements = relationship(
        "InventoryRestatement",
        foreign_keys="InventoryRestatement.original_inventory_id",
        back_populates="original_inventory",
    )
    audit_reports = relationship(
        "AuditReport",
        back_populates="inventory",
    )
