from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FactorSetStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class FactorImportStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DUPLICATE = "duplicate"


class GreenhouseGasComponent(StrEnum):
    TOTAL_CO2E = "total_co2e"
    CO2 = "co2"
    CH4 = "ch4"
    N2O = "n2o"
    OTHER = "other"


class EmissionFactorSet(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "emission_factor_sets"
    __table_args__ = (
        UniqueConstraint(
            "publisher",
            "dataset_name",
            "dataset_version",
            "source_sha256",
            name="uq_factor_set_source_version_hash",
        ),
    )

    publisher: Mapped[str] = mapped_column(String(250), nullable=False, index=True)
    dataset_name: Mapped[str] = mapped_column(String(300), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(100), nullable=False)
    reporting_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    publication_date: Mapped[date | None] = mapped_column(Date)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date] = mapped_column(Date, nullable=False)
    geography_code: Mapped[str] = mapped_column(String(20), nullable=False, default="GB")
    source_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_reference: Mapped[str | None] = mapped_column(String(1000))
    methodology_reference: Mapped[str | None] = mapped_column(String(1000))
    licence_name: Mapped[str | None] = mapped_column(String(250))
    licence_reference: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[FactorSetStatus] = mapped_column(
        Enum(FactorSetStatus, name="factor_set_status"),
        nullable=False,
        default=FactorSetStatus.DRAFT,
    )
    is_authoritative: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    imported_by: Mapped[str] = mapped_column(String(200), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(200))
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    superseded_by_set_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("emission_factor_sets.id", ondelete="SET NULL"),
    )
    notes: Mapped[str | None] = mapped_column(Text)

    factors = relationship(
        "EmissionFactor",
        back_populates="factor_set",
        cascade="all, delete-orphan",
    )
    import_jobs = relationship(
        "FactorImportJob",
        back_populates="factor_set",
    )


class EmissionFactor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "emission_factors"
    __table_args__ = (
        UniqueConstraint(
            "factor_set_id",
            "source_factor_id",
            name="uq_factor_set_source_factor_id",
        ),
    )

    factor_set_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("emission_factor_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_factor_id: Mapped[str] = mapped_column(String(150), nullable=False)
    scope: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    level_1: Mapped[str] = mapped_column(String(250), nullable=False, index=True)
    level_2: Mapped[str | None] = mapped_column(String(250), index=True)
    level_3: Mapped[str | None] = mapped_column(String(250), index=True)
    level_4: Mapped[str | None] = mapped_column(String(250), index=True)
    column_text: Mapped[str | None] = mapped_column(String(500))
    activity_unit: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    factor_unit_text: Mapped[str] = mapped_column(String(250), nullable=False)
    greenhouse_gas_component: Mapped[GreenhouseGasComponent] = mapped_column(
        Enum(GreenhouseGasComponent, name="greenhouse_gas_component"),
        nullable=False,
        index=True,
    )
    greenhouse_gas_label: Mapped[str] = mapped_column(String(100), nullable=False)
    factor_value: Mapped[Decimal] = mapped_column(Numeric(30, 15), nullable=False)
    factor_numerator_unit: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="kg CO2e",
    )
    factor_denominator_unit: Mapped[str] = mapped_column(String(100), nullable=False)
    geography_code: Mapped[str] = mapped_column(String(20), nullable=False, default="GB")
    reporting_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    lifecycle_boundary: Mapped[str | None] = mapped_column(String(150))
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_source_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    factor_set = relationship("EmissionFactorSet", back_populates="factors")


class FactorImportJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "factor_import_jobs"

    factor_set_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("emission_factor_sets.id", ondelete="SET NULL"),
        index=True,
    )
    status: Mapped[FactorImportStatus] = mapped_column(
        Enum(FactorImportStatus, name="factor_import_status"),
        nullable=False,
        default=FactorImportStatus.QUEUED,
    )
    source_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dataset_version: Mapped[str] = mapped_column(String(100), nullable=False)
    reporting_year: Mapped[int] = mapped_column(Integer, nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requested_by: Mapped[str] = mapped_column(String(200), nullable=False)
    failure_message: Mapped[str | None] = mapped_column(Text)

    factor_set = relationship("EmissionFactorSet", back_populates="import_jobs")
    errors = relationship(
        "FactorImportError",
        back_populates="import_job",
        cascade="all, delete-orphan",
    )


class FactorImportError(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "factor_import_errors"

    import_job_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("factor_import_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    worksheet_name: Mapped[str] = mapped_column(String(250), nullable=False)
    row_number: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str] = mapped_column(String(100), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    raw_row_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    import_job = relationship("FactorImportJob", back_populates="errors")
