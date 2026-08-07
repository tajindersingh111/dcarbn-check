from __future__ import annotations

from decimal import Decimal
from typing import Final

from app.integrations.data.hashing import canonical_json_sha256
from app.schemas.data_integration import (
    AccountingSourceSystem,
    DataAccountingScope3Payload,
    DataAccountingScope3TemplateResponse,
    DataOperationalEmissionPayload,
)

SUPPORTED_SUPPLIER_RESULT_CATEGORIES: Final[tuple[int, ...]] = (
    1,
    2,
    8,
    10,
    11,
    12,
    13,
    14,
    15,
)
ACCOUNTING_IMPORT_SCHEMA_VERSION: Final[str] = "1.0"
CALCULATION_SOFTWARE_VERSION: Final[str] = "dcarbn-carbon-platform-1"

REQUIRED_COLUMNS: Final[tuple[str, ...]] = (
    "external_customer_id",
    "external_transaction_id",
    "source_system",
    "transaction_date",
    "supplier_name",
    "description",
    "scope_3_category",
    "reported_kg_co2e",
    "allocation_percentage",
    "supplier_methodology",
    "supplier_methodology_version",
    "supplier_reporting_period_start",
    "supplier_reporting_period_end",
    "supplier_result_calculated_at",
    "boundary_description",
    "assurance_status",
    "evidence_reference",
)
OPTIONAL_COLUMNS: Final[tuple[str, ...]] = (
    "source_account_code",
    "source_account_name",
    "currency_code",
    "net_amount",
    "source_document_reference",
    "source_record_version",
)


def governed_scope3_method_id(category: int) -> str:
    if category not in SUPPORTED_SUPPLIER_RESULT_CATEGORIES:
        raise ValueError(f"Unsupported supplier-specific Scope 3 category: {category}")
    return (
        f"scope3.category{category}."
        "supplier_specific.reported_kgco2e.ghgp.v1"
    )


def accounting_scope3_template() -> DataAccountingScope3TemplateResponse:
    return DataAccountingScope3TemplateResponse(
        schema_version=ACCOUNTING_IMPORT_SCHEMA_VERSION,
        supported_source_systems=list(AccountingSourceSystem),
        required_columns=list(REQUIRED_COLUMNS),
        optional_columns=list(OPTIONAL_COLUMNS),
        governed_methods={
            category: governed_scope3_method_id(category)
            for category in SUPPORTED_SUPPLIER_RESULT_CATEGORIES
        },
    )


def normalise_scope3_accounting_result(
    item: DataAccountingScope3Payload,
) -> DataOperationalEmissionPayload:
    method_id = governed_scope3_method_id(item.scope_3_category)
    allocated_kg_co2e = (
        item.reported_kg_co2e
        * item.allocation_percentage
        / Decimal("100")
    )

    source_record = item.model_dump(mode="json")
    source_hash = canonical_json_sha256(source_record)
    external_calculation_id = (
        f"{item.source_system.value}:{item.external_transaction_id}:"
        f"scope3:{item.scope_3_category}"
    )

    accounting_reference = {
        "source_system": item.source_system.value,
        "external_transaction_id": item.external_transaction_id,
        "source_account_code": item.source_account_code,
        "source_account_name": item.source_account_name,
        "transaction_date": item.transaction_date.isoformat(),
        "currency_code": item.currency_code,
        "net_amount": str(item.net_amount) if item.net_amount is not None else None,
        "source_document_reference": item.source_document_reference,
    }
    supplier_lineage = {
        "supplier_name": item.supplier_name,
        "supplier_methodology": item.supplier_methodology,
        "supplier_methodology_version": item.supplier_methodology_version,
        "supplier_reporting_period_start": (
            item.supplier_reporting_period_start.isoformat()
        ),
        "supplier_reporting_period_end": (
            item.supplier_reporting_period_end.isoformat()
        ),
        "boundary_description": item.boundary_description,
        "assurance_status": item.assurance_status,
        "evidence_reference": item.evidence_reference,
    }

    return DataOperationalEmissionPayload(
        external_customer_id=item.external_customer_id,
        external_calculation_id=external_calculation_id,
        suggested_scope="scope_3",
        suggested_scope_3_category=item.scope_3_category,
        classification_reason=(
            "Governed supplier-specific result imported from "
            f"{item.source_system.value}; customer review required"
        ),
        methodology_version=item.supplier_methodology_version,
        external_activity_key=item.external_transaction_id,
        method_identifier=method_id,
        calculation_software_version=CALCULATION_SOFTWARE_VERSION,
        reporting_period_start=item.supplier_reporting_period_start,
        reporting_period_end=item.supplier_reporting_period_end,
        comparison_inputs={
            "reported_kg_co2e": str(item.reported_kg_co2e),
            "allocation_percentage": str(item.allocation_percentage),
            "allocated_kg_co2e": str(allocated_kg_co2e),
            "accounting_reference": accounting_reference,
        },
        total_kg_co2e=allocated_kg_co2e,
        calculated_at=item.supplier_result_calculated_at,
        source_record_version=item.source_record_version,
        source_hash=source_hash,
        lineage={
            "governed_method_id": method_id,
            "accounting_reference": accounting_reference,
            "supplier_lineage": supplier_lineage,
        },
        metadata={
            **item.metadata,
            "import_contract": "accounting_scope3_supplier_result",
            "governed_method_id": method_id,
            "supplier_lineage": supplier_lineage,
        },
    )
