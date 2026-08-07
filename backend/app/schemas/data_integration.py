from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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


class AccountingSourceSystem(StrEnum):
    CSV = "csv"
    QUICKBOOKS = "quickbooks"
    XERO = "xero"
    SAGE = "sage"
    API = "api"


class DataAccountingScope3Payload(BaseModel):
    external_customer_id: str = Field(min_length=1, max_length=200)
    external_transaction_id: str = Field(min_length=1, max_length=200)
    source_system: AccountingSourceSystem
    source_account_code: str | None = Field(default=None, max_length=100)
    source_account_name: str | None = Field(default=None, max_length=300)
    transaction_date: date
    supplier_name: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1, max_length=1000)
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    net_amount: Decimal | None = None
    scope_3_category: int = Field(ge=1, le=15)
    reported_kg_co2e: Decimal = Field(gt=0)
    allocation_percentage: Decimal = Field(default=Decimal("100"), gt=0, le=100)
    supplier_methodology: str = Field(min_length=1, max_length=300)
    supplier_methodology_version: str = Field(min_length=1, max_length=100)
    supplier_reporting_period_start: date
    supplier_reporting_period_end: date
    supplier_result_calculated_at: datetime
    boundary_description: str = Field(min_length=1, max_length=1000)
    assurance_status: str = Field(min_length=1, max_length=100)
    evidence_reference: str = Field(min_length=1, max_length=500)
    source_document_reference: str | None = Field(default=None, max_length=500)
    source_record_version: str | None = Field(default=None, max_length=100)
    metadata: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_supplier_specific_category(self) -> "DataAccountingScope3Payload":
        supported_categories = {1, 2, 8, 10, 11, 12, 13, 14, 15}
        if self.scope_3_category not in supported_categories:
            raise ValueError(
                "Accounting supplier-result imports support Scope 3 categories "
                "1, 2, 8 and 10-15"
            )
        if self.supplier_reporting_period_end < self.supplier_reporting_period_start:
            raise ValueError(
                "supplier_reporting_period_end must not precede "
                "supplier_reporting_period_start"
            )
        if self.currency_code is not None:
            self.currency_code = self.currency_code.upper()
        return self


class DataAccountingScope3TemplateResponse(BaseModel):
    schema_version: str
    supported_source_systems: list[AccountingSourceSystem]
    required_columns: list[str]
    optional_columns: list[str]
    governed_methods: dict[int, str]


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



class DataAccountingConnectionCreate(BaseModel):
    organisation_id: UUID
    external_customer_id: str = Field(min_length=1, max_length=200)
    provider: AccountingSourceSystem
    external_company_id: str = Field(min_length=1, max_length=200)
    display_name: str = Field(min_length=1, max_length=300)
    secret_reference: str | None = Field(default=None, max_length=500)
    mapping_profile_version: str = Field(min_length=1, max_length=100)
    mapping: dict[str, str]

    @field_validator("secret_reference")
    @classmethod
    def validate_secret_reference(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith(("secret://", "vault://")):
            raise ValueError(
                "secret_reference must be a secret-manager reference, not a credential"
            )
        return value


class DataAccountingConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    organisation_id: UUID
    external_customer_id: str
    provider: str
    external_company_id: str
    display_name: str
    status: str
    mapping_profile_version: str
    mapping_json: dict[str, str]
    last_cursor: str | None
    last_synced_at: datetime | None
    failure_code: str | None
    failure_message: str | None
    created_at: datetime
    updated_at: datetime


class DataAccountingSyncCreate(BaseModel):
    cursor: str | None = Field(default=None, max_length=1000)
    requested_from: datetime | None = None
    requested_to: datetime | None = None

    @model_validator(mode="after")
    def validate_window(self) -> "DataAccountingSyncCreate":
        if (
            self.requested_from is not None
            and self.requested_to is not None
            and self.requested_to < self.requested_from
        ):
            raise ValueError("requested_to must not precede requested_from")
        return self


class DataAccountingSyncResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    connection_id: UUID
    sync_identity: str
    cursor_before: str | None
    cursor_after: str | None
    requested_from: datetime | None
    requested_to: datetime | None
    status: str
    records_received: int
    records_imported: int
    records_rejected: int
    requested_by: str
    started_at: datetime | None
    completed_at: datetime | None
    failure_code: str | None
    failure_message: str | None
    diagnostics_json: dict[str, object]
    created_at: datetime
    updated_at: datetime
