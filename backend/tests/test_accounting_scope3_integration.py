from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.integrations.data.accounting_scope3 import (
    accounting_scope3_template,
    governed_scope3_method_id,
    normalise_scope3_accounting_result,
)
from app.schemas.data_integration import (
    AccountingSourceSystem,
    DataAccountingScope3Payload,
)


def make_payload(
    *,
    category: int = 1,
    source_system: AccountingSourceSystem = AccountingSourceSystem.XERO,
) -> DataAccountingScope3Payload:
    return DataAccountingScope3Payload(
        external_customer_id="customer-1042",
        external_transaction_id=f"txn-{category}-001",
        source_system=source_system,
        source_account_code="5000",
        source_account_name="Purchased materials",
        transaction_date=date(2026, 3, 31),
        supplier_name="Example Supplier Ltd",
        description="Supplier-specific attributable lifecycle result",
        currency_code="gbp",
        net_amount=Decimal("12500.00"),
        scope_3_category=category,
        reported_kg_co2e=Decimal("1000"),
        allocation_percentage=Decimal("75"),
        supplier_methodology="GHG Protocol supplier-specific method",
        supplier_methodology_version="2026.1",
        supplier_reporting_period_start=date(2026, 1, 1),
        supplier_reporting_period_end=date(2026, 12, 31),
        supplier_result_calculated_at=datetime(2026, 7, 1, tzinfo=UTC),
        boundary_description="Cradle-to-gate attributable emissions",
        assurance_status="third_party_verified",
        evidence_reference="supplier-assurance-2026.pdf",
        source_document_reference="bill-1001",
        source_record_version="4",
    )


@pytest.mark.parametrize("category", [1, 2, 8, 10, 11, 12, 13, 14, 15])
def test_accounting_contract_normalises_each_supplier_result_category(
    category: int,
) -> None:
    result = normalise_scope3_accounting_result(make_payload(category=category))

    assert result.suggested_scope == "scope_3"
    assert result.suggested_scope_3_category == category
    assert result.total_kg_co2e == Decimal("750")
    assert result.method_identifier == governed_scope3_method_id(category)
    assert result.external_calculation_id == f"xero:txn-{category}-001:scope3:{category}"
    assert result.comparison_inputs["allocation_percentage"] == "75"
    assert result.lineage["accounting_reference"]["source_account_code"] == "5000"
    assert (
        result.lineage["supplier_lineage"]["evidence_reference"]
        == "supplier-assurance-2026.pdf"
    )
    assert len(result.source_hash) == 64


def test_accounting_contract_rejects_category_with_activity_factor_route() -> None:
    with pytest.raises(
        ValidationError,
        match="Accounting supplier-result imports support Scope 3 categories",
    ):
        make_payload(category=4)


def test_accounting_contract_rejects_reversed_supplier_period() -> None:
    with pytest.raises(
        ValidationError,
        match="supplier_reporting_period_end must not precede",
    ):
        DataAccountingScope3Payload(
            **{
                **make_payload().model_dump(),
                "supplier_reporting_period_start": date(2026, 12, 31),
                "supplier_reporting_period_end": date(2026, 1, 1),
            }
        )


def test_accounting_contract_hash_is_deterministic() -> None:
    first = normalise_scope3_accounting_result(make_payload())
    second = normalise_scope3_accounting_result(make_payload())

    assert first.source_hash == second.source_hash
    assert first.external_calculation_id == second.external_calculation_id


def test_accounting_template_lists_sources_columns_and_methods() -> None:
    template = accounting_scope3_template()

    assert set(template.supported_source_systems) == {
        AccountingSourceSystem.CSV,
        AccountingSourceSystem.QUICKBOOKS,
        AccountingSourceSystem.XERO,
        AccountingSourceSystem.SAGE,
        AccountingSourceSystem.API,
    }
    assert "evidence_reference" in template.required_columns
    assert "source_account_code" in template.optional_columns
    assert set(template.governed_methods) == {1, 2, 8, 10, 11, 12, 13, 14, 15}
