from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Organisation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organisations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_organisation_tenant_name"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(250))
    registration_number: Mapped[str | None] = mapped_column(String(100))
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    tenant = relationship("Tenant", back_populates="organisations")
    legal_entities = relationship(
        "LegalEntity",
        back_populates="organisation",
        cascade="all, delete-orphan",
    )
    sites = relationship(
        "Site",
        back_populates="organisation",
        cascade="all, delete-orphan",
    )
    reporting_periods = relationship(
        "ReportingPeriod",
        back_populates="organisation",
        cascade="all, delete-orphan",
    )


class LegalEntity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "legal_entities"

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
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    registration_number: Mapped[str | None] = mapped_column(String(100))
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    ownership_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    organisation = relationship("Organisation", back_populates="legal_entities")
    boundary_memberships = relationship(
        "BoundaryMembership",
        back_populates="legal_entity",
    )


class Site(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sites"

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
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    site_type: Mapped[str] = mapped_column(String(100), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    postcode: Mapped[str | None] = mapped_column(String(30))

    organisation = relationship("Organisation", back_populates="sites")
