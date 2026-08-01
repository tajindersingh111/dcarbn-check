from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DataReviewStatus(StrEnum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONVERTED = "converted"


class DataOperationalEmissionReview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "data_operational_emission_reviews"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "operational_emission_id",
            name="uq_data_review_operational_emission",
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    operational_emission_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("data_operational_emissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    inventory_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inventories.id", ondelete="RESTRICT"),
        index=True,
    )
    status: Mapped[DataReviewStatus] = mapped_column(
        Enum(DataReviewStatus, name="data_review_status"),
        nullable=False,
        default=DataReviewStatus.PENDING,
        index=True,
    )
    reviewer_id: Mapped[str | None] = mapped_column(String(200))
    review_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewer_comment: Mapped[str | None] = mapped_column(Text)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    conversion_failure: Mapped[str | None] = mapped_column(Text)
    calculation_run_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("calculation_runs.id", ondelete="RESTRICT"),
        unique=True,
    )
    calculation_result_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("calculation_results.id", ondelete="RESTRICT"),
        unique=True,
    )
    activity_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("activity_records.id", ondelete="RESTRICT"),
        unique=True,
    )
    review_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    operational_emission = relationship(
        "DataOperationalEmission",
        back_populates="review",
    )
    calculation_run = relationship("CalculationRun")
    calculation_result = relationship("CalculationResult")
    activity = relationship("ActivityRecord")
