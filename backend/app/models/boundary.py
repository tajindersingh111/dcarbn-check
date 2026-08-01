from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
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

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ConsolidationApproach(StrEnum):
    OPERATIONAL_CONTROL = "operational_control"
    FINANCIAL_CONTROL = "financial_control"
    EQUITY_SHARE = "equity_share"


class BoundaryStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    LOCKED = "locked"
    SUPERSEDED = "superseded"


class MembershipDecision(StrEnum):
    AUTO = "auto"
    INCLUDED = "included"
    EXCLUDED = "excluded"


class OrganisationalBoundary(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organisational_boundaries"
    __table_args__ = (
        UniqueConstraint(
            "reporting_period_id",
            "version",
            name="uq_boundary_reporting_period_version",
        ),
        CheckConstraint(
            "control_threshold_percentage >= 0 "
            "AND control_threshold_percentage <= 100",
            name="boundary_control_threshold_range",
        ),
    )

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
    consolidation_approach: Mapped[ConsolidationApproach] = mapped_column(
        Enum(ConsolidationApproach, name="consolidation_approach"),
        nullable=False,
    )
    status: Mapped[BoundaryStatus] = mapped_column(
        Enum(BoundaryStatus, name="boundary_status"),
        nullable=False,
        default=BoundaryStatus.DRAFT,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    control_threshold_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("50.00"),
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date] = mapped_column(Date, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(200))
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    reporting_period = relationship(
        "ReportingPeriod",
        back_populates="organisational_boundaries",
    )
    memberships = relationship(
        "BoundaryMembership",
        back_populates="boundary",
        cascade="all, delete-orphan",
    )


class BoundaryMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "boundary_memberships"
    __table_args__ = (
        UniqueConstraint(
            "boundary_id",
            "legal_entity_id",
            "effective_from",
            name="uq_boundary_membership_entity_effective_from",
        ),
        CheckConstraint(
            "ownership_percentage >= 0 AND ownership_percentage <= 100",
            name="membership_ownership_range",
        ),
        CheckConstraint(
            "allocation_percentage >= 0 AND allocation_percentage <= 100",
            name="membership_allocation_range",
        ),
        CheckConstraint(
            "effective_to >= effective_from",
            name="membership_effective_dates",
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    boundary_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organisational_boundaries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    legal_entity_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("legal_entities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    decision: Mapped[MembershipDecision] = mapped_column(
        Enum(MembershipDecision, name="membership_decision"),
        nullable=False,
        default=MembershipDecision.AUTO,
    )
    ownership_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    has_operational_control: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    has_financial_control: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    is_included: Mapped[bool] = mapped_column(Boolean, nullable=False)
    allocation_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date] = mapped_column(Date, nullable=False)
    decision_reason: Mapped[str | None] = mapped_column(Text)
    evidence_reference: Mapped[str | None] = mapped_column(String(500))

    boundary = relationship("OrganisationalBoundary", back_populates="memberships")
    legal_entity = relationship("LegalEntity", back_populates="boundary_memberships")
