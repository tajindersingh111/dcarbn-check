from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
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


class ActivityStatus(StrEnum):
    DRAFT = "draft"
    VALIDATED = "validated"
    CALCULATED = "calculated"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ActivityType(StrEnum):
    MOBILE_COMBUSTION = "mobile_combustion"
    STATIONARY_COMBUSTION = "stationary_combustion"
    REFRIGERANT = "refrigerant"
    PURCHASED_ELECTRICITY = "purchased_electricity"
    PURCHASED_HEAT_STEAM_COOLING = "purchased_heat_steam_cooling"
    FREIGHT_TRANSPORT = "freight_transport"
    BUSINESS_TRAVEL = "business_travel"
    EMPLOYEE_COMMUTING = "employee_commuting"


class EmissionScope(StrEnum):
    SCOPE_1 = "scope_1"
    SCOPE_2 = "scope_2"
    SCOPE_3 = "scope_3"


class Scope2Method(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    LOCATION_BASED = "location_based"
    MARKET_BASED = "market_based"


class DataQualityLevel(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    ESTIMATED = "estimated"
    UNKNOWN = "unknown"


class ActivityRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "activity_records"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "source_system",
            "source_record_id",
            "version",
            name="uq_activity_source_version",
        ),
        CheckConstraint(
            "activity_value >= 0",
            name="activity_value_non_negative",
        ),
        CheckConstraint(
            "allocation_percentage >= 0 AND allocation_percentage <= 100",
            name="activity_allocation_range",
        ),
        CheckConstraint(
            "data_quality_score >= 0 AND data_quality_score <= 100",
            name="activity_data_quality_range",
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
    organisation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organisations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    legal_entity_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("legal_entities.id", ondelete="RESTRICT"),
        index=True,
    )
    site_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sites.id", ondelete="RESTRICT"),
        index=True,
    )
    activity_type: Mapped[ActivityType] = mapped_column(
        Enum(ActivityType, name="activity_type"),
        nullable=False,
        index=True,
    )
    status: Mapped[ActivityStatus] = mapped_column(
        Enum(ActivityStatus, name="activity_status"),
        nullable=False,
        default=ActivityStatus.DRAFT,
        index=True,
    )
    scope: Mapped[EmissionScope] = mapped_column(
        Enum(EmissionScope, name="emission_scope"),
        nullable=False,
        index=True,
    )
    scope_3_category: Mapped[int | None] = mapped_column(Integer, index=True)
    scope_2_method: Mapped[Scope2Method] = mapped_column(
        Enum(Scope2Method, name="scope_2_method"),
        nullable=False,
        default=Scope2Method.NOT_APPLICABLE,
    )
    activity_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    activity_value: Mapped[Decimal] = mapped_column(
        Numeric(30, 15),
        nullable=False,
    )
    activity_unit: Mapped[str] = mapped_column(String(100), nullable=False)
    normalized_value: Mapped[Decimal | None] = mapped_column(Numeric(30, 15))
    normalized_unit: Mapped[str | None] = mapped_column(String(100))
    geography_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="GB",
    )
    factor_level_1: Mapped[str | None] = mapped_column(String(250))
    factor_level_2: Mapped[str | None] = mapped_column(String(250))
    factor_level_3: Mapped[str | None] = mapped_column(String(250))
    factor_level_4: Mapped[str | None] = mapped_column(String(250))
    factor_column_text: Mapped[str | None] = mapped_column(String(500))
    lifecycle_boundary: Mapped[str | None] = mapped_column(String(150))
    allocation_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("100.00"),
    )
    data_quality_level: Mapped[DataQualityLevel] = mapped_column(
        Enum(DataQualityLevel, name="data_quality_level"),
        nullable=False,
        default=DataQualityLevel.UNKNOWN,
    )
    data_quality_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    source_system: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="carbon-platform",
    )
    source_record_id: Mapped[str] = mapped_column(String(200), nullable=False)
    source_record_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_reference: Mapped[str | None] = mapped_column(String(1000))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    superseded_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("activity_records.id", ondelete="SET NULL"),
    )
    validation_message: Mapped[str | None] = mapped_column(Text)

    inventory = relationship("Inventory", back_populates="activities")
    calculation_results = relationship(
        "CalculationResult",
        back_populates="activity",
    )
