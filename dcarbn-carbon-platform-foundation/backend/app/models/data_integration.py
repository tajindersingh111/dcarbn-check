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


class DataImportStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    DUPLICATE = "duplicate"


class DataRecordType(StrEnum):
    VEHICLE = "vehicle"
    SHIPMENT = "shipment"
    JOURNEY = "journey"
    FUEL = "fuel"
    PAYLOAD = "payload"
    OPERATIONAL_EMISSION = "operational_emission"


class DataClassificationStatus(StrEnum):
    SUGGESTED = "suggested"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    REVIEW_REQUIRED = "review_required"


class DataOrganisationMapping(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "data_organisation_mappings"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "external_customer_id",
            name="uq_data_mapping_external_customer",
        ),
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
    external_customer_id: Mapped[str] = mapped_column(String(200), nullable=False)
    external_customer_name: Mapped[str | None] = mapped_column(String(300))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    mapping_notes: Mapped[str | None] = mapped_column(Text)


class DataImportBatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "data_import_batches"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_data_import_batch_idempotency",
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    schema_version: Mapped[str] = mapped_column(String(50), nullable=False)
    record_type: Mapped[DataRecordType] = mapped_column(
        Enum(DataRecordType, name="data_record_type"),
        nullable=False,
        index=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    source_payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[DataImportStatus] = mapped_column(
        Enum(DataImportStatus, name="data_import_status"),
        nullable=False,
        default=DataImportStatus.QUEUED,
        index=True,
    )
    records_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_imported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requested_by: Mapped[str] = mapped_column(String(200), nullable=False)
    failure_message: Mapped[str | None] = mapped_column(Text)

    errors = relationship(
        "DataImportError",
        back_populates="batch",
        cascade="all, delete-orphan",
    )


class DataImportError(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "data_import_errors"

    batch_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("data_import_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    record_index: Mapped[int | None] = mapped_column(Integer)
    external_record_id: Mapped[str | None] = mapped_column(String(200))
    error_code: Mapped[str] = mapped_column(String(100), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    raw_record: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    batch = relationship("DataImportBatch", back_populates="errors")


class DataVehicle(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "data_vehicles"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "external_vehicle_id",
            name="uq_data_vehicle_external_id",
        ),
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
    external_vehicle_id: Mapped[str] = mapped_column(String(200), nullable=False)
    registration_number: Mapped[str | None] = mapped_column(String(100))
    vehicle_type: Mapped[str] = mapped_column(String(150), nullable=False)
    fuel_type: Mapped[str | None] = mapped_column(String(100))
    gross_vehicle_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(18, 3))
    model_year: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source_record_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DataShipment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "data_shipments"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "external_shipment_id",
            name="uq_data_shipment_external_id",
        ),
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
    external_shipment_id: Mapped[str] = mapped_column(String(200), nullable=False)
    external_consignment_id: Mapped[str | None] = mapped_column(String(200))
    shipment_date: Mapped[date | None] = mapped_column(Date)
    origin_country_code: Mapped[str | None] = mapped_column(String(20))
    origin_postcode: Mapped[str | None] = mapped_column(String(30))
    destination_country_code: Mapped[str | None] = mapped_column(String(20))
    destination_postcode: Mapped[str | None] = mapped_column(String(30))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source_record_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DataJourney(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "data_journeys"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "external_journey_id",
            name="uq_data_journey_external_id",
        ),
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
    external_journey_id: Mapped[str] = mapped_column(String(200), nullable=False)
    vehicle_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("data_vehicles.id", ondelete="SET NULL"),
        index=True,
    )
    shipment_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("data_shipments.id", ondelete="SET NULL"),
        index=True,
    )
    journey_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    journey_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    distance_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    distance_unit: Mapped[str | None] = mapped_column(String(100))
    distance_source: Mapped[str | None] = mapped_column(String(100))
    route_reference: Mapped[str | None] = mapped_column(String(300))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source_record_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DataFuelRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "data_fuel_records"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "external_fuel_record_id",
            name="uq_data_fuel_external_id",
        ),
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
    external_fuel_record_id: Mapped[str] = mapped_column(String(200), nullable=False)
    journey_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("data_journeys.id", ondelete="SET NULL"),
        index=True,
    )
    vehicle_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("data_vehicles.id", ondelete="SET NULL"),
        index=True,
    )
    fuel_type: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity_value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    quantity_unit: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity_source: Mapped[str | None] = mapped_column(String(100))
    transaction_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source_record_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class DataPayloadRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "data_payload_records"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "external_payload_record_id",
            name="uq_data_payload_external_id",
        ),
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
    external_payload_record_id: Mapped[str] = mapped_column(String(200), nullable=False)
    journey_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("data_journeys.id", ondelete="SET NULL"),
        index=True,
    )
    shipment_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("data_shipments.id", ondelete="SET NULL"),
        index=True,
    )
    quantity_value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    quantity_unit: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity_source: Mapped[str | None] = mapped_column(String(100))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source_record_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class DataOperationalEmission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "data_operational_emissions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "external_calculation_id",
            name="uq_data_operational_emission_external_id",
        ),
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
    external_calculation_id: Mapped[str] = mapped_column(String(200), nullable=False)
    journey_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("data_journeys.id", ondelete="SET NULL"),
        index=True,
    )
    shipment_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("data_shipments.id", ondelete="SET NULL"),
        index=True,
    )
    vehicle_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("data_vehicles.id", ondelete="SET NULL"),
        index=True,
    )
    activity_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("activity_records.id", ondelete="SET NULL"),
        index=True,
    )
    suggested_scope: Mapped[str | None] = mapped_column(String(50))
    suggested_scope_3_category: Mapped[int | None] = mapped_column(Integer)
    classification_reason: Mapped[str | None] = mapped_column(Text)
    classification_status: Mapped[DataClassificationStatus] = mapped_column(
        Enum(DataClassificationStatus, name="data_classification_status"),
        nullable=False,
        default=DataClassificationStatus.SUGGESTED,
        index=True,
    )
    confirmed_scope: Mapped[str | None] = mapped_column(String(50))
    confirmed_scope_3_category: Mapped[int | None] = mapped_column(Integer)
    methodology_version: Mapped[str] = mapped_column(String(100), nullable=False)
    total_kg_co2e: Mapped[Decimal] = mapped_column(Numeric(30, 15), nullable=False)
    co2_kg: Mapped[Decimal | None] = mapped_column(Numeric(30, 15))
    ch4_kg_co2e: Mapped[Decimal | None] = mapped_column(Numeric(30, 15))
    n2o_kg_co2e: Mapped[Decimal | None] = mapped_column(Numeric(30, 15))
    data_quality_level: Mapped[str | None] = mapped_column(String(50))
    data_quality_score: Mapped[int | None] = mapped_column(Integer)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_record_version: Mapped[str | None] = mapped_column(String(100))
    source_record_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    lineage_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    review = relationship(
        "DataOperationalEmissionReview",
        back_populates="operational_emission",
        uselist=False,
    )
