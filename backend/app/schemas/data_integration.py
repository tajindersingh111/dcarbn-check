from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.data_integration import (
    DataClassificationStatus,
    DataImportStatus,
    DataRecordType,
)


class DataOrganisationMappingCreate(BaseModel):
    organisation_id: UUID
    external_customer_id: str = Field(min_length=1, max_length=200)
    external_customer_name: str | None = Field(default=None, max_length=300)
    mapping_notes: str | None = Field(default=None, max_length=5000)


class DataOrganisationMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    organisation_id: UUID
    external_customer_id: str
    external_customer_name: str | None
    is_active: bool
    mapping_notes: str | None


class DataBatchEnvelope(BaseModel):
    schema_version: str = Field(default="1.0", min_length=1, max_length=50)
    idempotency_key: str = Field(min_length=1, max_length=200)


class DataVehiclePayload(BaseModel):
    external_customer_id: str
    external_vehicle_id: str
    registration_number: str | None = None
    vehicle_type: str
    fuel_type: str | None = None
    gross_vehicle_weight_kg: Decimal | None = Field(default=None, ge=0)
    model_year: int | None = Field(default=None, ge=1900, le=2200)
    source_updated_at: datetime | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class DataShipmentPayload(BaseModel):
    external_customer_id: str
    external_shipment_id: str
    external_consignment_id: str | None = None
    shipment_date: date | None = None
    origin_country_code: str | None = None
    origin_postcode: str | None = None
    destination_country_code: str | None = None
    destination_postcode: str | None = None
    source_updated_at: datetime | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class DataJourneyPayload(BaseModel):
    external_customer_id: str
    external_journey_id: str
    external_vehicle_id: str | None = None
    external_shipment_id: str | None = None
    journey_started_at: datetime | None = None
    journey_completed_at: datetime | None = None
    distance_value: Decimal | None = Field(default=None, ge=0)
    distance_unit: str | None = None
    distance_source: str | None = None
    route_reference: str | None = None
    source_updated_at: datetime | None = None
    metadata: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_distance(self) -> "DataJourneyPayload":
        if (self.distance_value is None) != (self.distance_unit is None):
            raise ValueError("distance_value and distance_unit must be supplied together")
        return self


class DataFuelPayload(BaseModel):
    external_customer_id: str
    external_fuel_record_id: str
    external_journey_id: str | None = None
    external_vehicle_id: str | None = None
    fuel_type: str
    quantity_value: Decimal = Field(gt=0)
    quantity_unit: str
    quantity_source: str | None = None
    transaction_at: datetime | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class DataPayloadPayload(BaseModel):
    external_customer_id: str
    external_payload_record_id: str
    external_journey_id: str | None = None
    external_shipment_id: str | None = None
    quantity_value: Decimal = Field(gt=0)
    quantity_unit: str
    quantity_source: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class DataOperationalEmissionPayload(BaseModel):
    external_customer_id: str
    external_calculation_id: str
    external_journey_id: str | None = None
    external_shipment_id: str | None = None
    external_vehicle_id: str | None = None
    suggested_scope: str | None = None
    suggested_scope_3_category: int | None = Field(default=None, ge=1, le=15)
    classification_reason: str | None = None
    methodology_version: str
    external_activity_key: str | None = Field(default=None, min_length=1, max_length=200)
    method_identifier: str | None = Field(default=None, min_length=1, max_length=200)
    calculation_software_version: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    reporting_period_start: date | None = None
    reporting_period_end: date | None = None
    uncertainty_percentage: Decimal | None = Field(default=None, ge=0)
    comparison_inputs: dict[str, object] = Field(default_factory=dict)
    total_kg_co2e: Decimal = Field(ge=0)
    co2_kg: Decimal | None = Field(default=None, ge=0)
    ch4_kg_co2e: Decimal | None = Field(default=None, ge=0)
    n2o_kg_co2e: Decimal | None = Field(default=None, ge=0)
    data_quality_level: str | None = None
    data_quality_score: int | None = Field(default=None, ge=0, le=100)
    calculated_at: datetime
    source_record_version: str | None = None
    source_hash: str = Field(min_length=8, max_length=128)
    lineage: dict[str, object] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_comparison_contract(self) -> "DataOperationalEmissionPayload":
        if (self.reporting_period_start is None) != (self.reporting_period_end is None):
            raise ValueError(
                "reporting_period_start and reporting_period_end must be supplied together"
            )
        if (
            self.reporting_period_start is not None
            and self.reporting_period_end is not None
            and self.reporting_period_end < self.reporting_period_start
        ):
            raise ValueError("reporting_period_end must not precede reporting_period_start")
        comparison_fields = (
            self.external_activity_key,
            self.method_identifier,
            self.calculation_software_version,
        )
        if any(value is not None for value in comparison_fields) and not all(
            value is not None for value in comparison_fields
        ):
            raise ValueError(
                "external_activity_key, method_identifier and "
                "calculation_software_version must be supplied together"
            )
        return self


T = TypeVar("T")


class DataBatchRequest(BaseModel, Generic[T]):
    schema_version: str = Field(default="1.0", min_length=1, max_length=50)
    idempotency_key: str = Field(min_length=1, max_length=200)
    records: list[T] = Field(min_length=1, max_length=10000)


class DataImportBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    schema_version: str
    record_type: DataRecordType
    idempotency_key: str
    source_payload_sha256: str
    status: DataImportStatus
    records_received: int
    records_imported: int
    records_rejected: int
    started_at: datetime | None
    completed_at: datetime | None
    requested_by: str
    failure_message: str | None


class DataImportErrorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    batch_id: UUID
    record_index: int | None
    external_record_id: str | None
    error_code: str
    error_message: str
    raw_record: dict[str, object] | None
    created_at: datetime


class DataClassificationConfirmRequest(BaseModel):
    activity_id: UUID | None = None
    confirmed_scope: str
    confirmed_scope_3_category: int | None = Field(default=None, ge=1, le=15)
    classification_status: DataClassificationStatus = (
        DataClassificationStatus.CONFIRMED
    )

    @model_validator(mode="after")
    def validate_category(self) -> "DataClassificationConfirmRequest":
        normalized = self.confirmed_scope.strip().lower().replace(" ", "_")
        if normalized == "scope_3" and self.confirmed_scope_3_category is None:
            raise ValueError("Scope 3 confirmation requires a category")
        if normalized != "scope_3" and self.confirmed_scope_3_category is not None:
            raise ValueError("Only Scope 3 confirmation may include a category")
        return self


class DataOperationalEmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    organisation_id: UUID
    external_calculation_id: str
    activity_id: UUID | None
    suggested_scope: str | None
    suggested_scope_3_category: int | None
    classification_status: DataClassificationStatus
    confirmed_scope: str | None
    confirmed_scope_3_category: int | None
    methodology_version: str
    external_activity_key: str | None
    method_identifier: str | None
    calculation_software_version: str | None
    reporting_period_start: date | None
    reporting_period_end: date | None
    uncertainty_percentage: Decimal | None
    comparison_inputs_json: dict[str, object]
    total_kg_co2e: Decimal
    co2_kg: Decimal | None
    ch4_kg_co2e: Decimal | None
    n2o_kg_co2e: Decimal | None
    data_quality_level: str | None
    data_quality_score: int | None
    calculated_at: datetime
    source_record_version: str | None
    source_record_hash: str


class DataReconciliationResponse(BaseModel):
    tenant_id: UUID
    mappings: int
    vehicles: int
    shipments: int
    journeys: int
    fuel_records: int
    payload_records: int
    operational_emissions: int
    unclassified_operational_emissions: int
    linked_activities: int
