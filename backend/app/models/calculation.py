from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.activity import EmissionScope, Scope2Method
from sqlalchemy import (
    JSON,
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


class CalculationRunStatus(StrEnum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    APPROVED = "approved"
    SUPERSEDED = "superseded"


class CalculationMethod(StrEnum):
    ACTIVITY_FACTOR = "activity_factor"
    EXTERNAL_OPERATIONAL_RESULT = "external_operational_result"
    SUPPLIER_SPECIFIC_RESULT = "supplier_specific_result"


class CalculationRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "calculation_runs"
    __table_args__ = (
        UniqueConstraint(
            "inventory_id",
            "version",
            name="uq_calculation_run_inventory_version",
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
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[CalculationRunStatus] = mapped_column(
        Enum(CalculationRunStatus, name="calculation_run_status"),
        nullable=False,
        default=CalculationRunStatus.DRAFT,
        index=True,
    )
    software_version: Mapped[str] = mapped_column(String(100), nullable=False)
    factor_policy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(200))
    activity_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_message: Mapped[str | None] = mapped_column(Text)

    inventory = relationship("Inventory", back_populates="calculation_runs")
    results = relationship(
        "CalculationResult",
        back_populates="calculation_run",
        cascade="all, delete-orphan",
    )


class CalculationResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "calculation_results"
    __table_args__ = (
        UniqueConstraint(
            "calculation_run_id",
            "activity_id",
            name="uq_calculation_result_run_activity",
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    calculation_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("calculation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("activity_records.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    factor_resolution_record_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("factor_resolution_records.id", ondelete="RESTRICT"),
        index=True,
    )
    selected_factor_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("emission_factors.id", ondelete="RESTRICT"),
        index=True,
    )
    method: Mapped[CalculationMethod] = mapped_column(
        Enum(CalculationMethod, name="calculation_method"),
        nullable=False,
    )
    scope: Mapped[EmissionScope] = mapped_column(
        Enum(EmissionScope, name="emission_scope", create_constraint=False),
        nullable=False,
        index=True,
    )
    scope_3_category: Mapped[int | None] = mapped_column(Integer, index=True)
    scope_2_method: Mapped[Scope2Method] = mapped_column(
        Enum(Scope2Method, name="scope_2_method", create_constraint=False),
        nullable=False,
    )
    original_activity_value: Mapped[Decimal] = mapped_column(
        Numeric(30, 15),
        nullable=False,
    )
    original_activity_unit: Mapped[str] = mapped_column(String(100), nullable=False)
    factor_activity_value: Mapped[Decimal] = mapped_column(
        Numeric(30, 15),
        nullable=False,
    )
    factor_activity_unit: Mapped[str] = mapped_column(String(100), nullable=False)
    factor_value: Mapped[Decimal | None] = mapped_column(Numeric(30, 15))
    allocation_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    allocation_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(10, 8),
        nullable=False,
    )
    gross_kg_co2e: Mapped[Decimal] = mapped_column(
        Numeric(30, 15),
        nullable=False,
    )
    allocated_kg_co2e: Mapped[Decimal] = mapped_column(
        Numeric(30, 15),
        nullable=False,
    )
    co2_kg: Mapped[Decimal | None] = mapped_column(Numeric(30, 15))
    ch4_kg_co2e: Mapped[Decimal | None] = mapped_column(Numeric(30, 15))
    n2o_kg_co2e: Mapped[Decimal | None] = mapped_column(Numeric(30, 15))
    calculation_formula: Mapped[str] = mapped_column(String(500), nullable=False)
    intermediate_values: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    methodology_version: Mapped[str] = mapped_column(String(100), nullable=False)

    calculation_run = relationship("CalculationRun", back_populates="results")
    activity = relationship("ActivityRecord", back_populates="calculation_results")
