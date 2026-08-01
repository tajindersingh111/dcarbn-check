from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Integer, JSON, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.factors.resolution import MatchStrength, ResolutionOutcome


class ResolutionSource(StrEnum):
    API = "api"
    CALCULATION_ENGINE = "calculation_engine"
    DATa_IMPORT = "data_import"
    MANUAL = "manual"


class FactorResolutionRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "factor_resolution_records"

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    inventory_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inventories.id", ondelete="SET NULL"),
        index=True,
    )
    selected_factor_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("emission_factors.id", ondelete="RESTRICT"),
        index=True,
    )
    outcome: Mapped[ResolutionOutcome] = mapped_column(
        Enum(ResolutionOutcome, name="resolution_outcome"),
        nullable=False,
        index=True,
    )
    match_strength: Mapped[MatchStrength | None] = mapped_column(
        Enum(MatchStrength, name="factor_match_strength"),
    )
    source: Mapped[ResolutionSource] = mapped_column(
        Enum(ResolutionSource, name="resolution_source"),
        nullable=False,
        default=ResolutionSource.API,
    )
    original_activity_value: Mapped[Decimal] = mapped_column(
        Numeric(30, 15),
        nullable=False,
    )
    original_activity_unit: Mapped[str] = mapped_column(String(100), nullable=False)
    normalized_activity_value: Mapped[Decimal | None] = mapped_column(
        Numeric(30, 15),
    )
    normalized_activity_unit: Mapped[str | None] = mapped_column(String(100))
    selected_factor_activity_value: Mapped[Decimal | None] = mapped_column(
        Numeric(30, 15),
    )
    selected_factor_activity_unit: Mapped[str | None] = mapped_column(String(100))
    selected_factor_value: Mapped[Decimal | None] = mapped_column(
        Numeric(30, 15),
    )
    resulting_kg_co2e: Mapped[Decimal | None] = mapped_column(
        Numeric(30, 15),
    )
    selected_score: Mapped[int | None] = mapped_column(Integer)
    criteria: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    candidate_summary: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    resolution_reason: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[str] = mapped_column(String(200), nullable=False)

    selected_factor = relationship("EmissionFactor")
