from decimal import Decimal
from uuid import UUID

from app.main import app
from app.models.activity import EmissionScope, Scope2Method
from app.schemas.calculation import (
    InventoryCalculationSummary,
    InventoryScopeSummaryItem,
    Scope2HeadlineBasis,
)
from app.services.calculations import calculate_inventory_totals


def _item(
    scope: EmissionScope,
    value: str,
    *,
    scope_2_method: Scope2Method = Scope2Method.NOT_APPLICABLE,
    scope_3_category: int | None = None,
) -> InventoryScopeSummaryItem:
    kg_co2e = Decimal(value)
    return InventoryScopeSummaryItem(
        scope=scope,
        scope_3_category=scope_3_category,
        scope_2_method=scope_2_method,
        kg_co2e=kg_co2e,
        t_co2e=kg_co2e / Decimal("1000"),
    )


ITEMS = [
    _item(EmissionScope.SCOPE_1, "100"),
    _item(
        EmissionScope.SCOPE_2,
        "40",
        scope_2_method=Scope2Method.LOCATION_BASED,
    ),
    _item(
        EmissionScope.SCOPE_2,
        "25",
        scope_2_method=Scope2Method.MARKET_BASED,
    ),
    _item(EmissionScope.SCOPE_3, "300", scope_3_category=4),
]


def test_location_based_headline_does_not_add_market_based_scope_2() -> None:
    totals = calculate_inventory_totals(
        ITEMS,
        Scope2HeadlineBasis.LOCATION_BASED,
    )

    assert totals["scope_2_location_based"] == Decimal("40")
    assert totals["scope_2_market_based"] == Decimal("25")
    assert totals["headline_total"] == Decimal("440")


def test_market_based_headline_does_not_add_location_based_scope_2() -> None:
    totals = calculate_inventory_totals(
        ITEMS,
        Scope2HeadlineBasis.MARKET_BASED,
    )

    assert totals["headline_total"] == Decimal("425")


def test_summary_api_requires_explicit_scope_2_headline_basis() -> None:
    openapi = app.openapi()
    summary_operation = next(
        operation["get"]
        for path, operation in openapi["paths"].items()
        if path.endswith("/calculation-runs/{run_id}/summary")
    )
    parameter = next(
        item
        for item in summary_operation["parameters"]
        if item["name"] == "scope_2_headline_basis"
    )

    assert parameter["required"] is True
    schema = parameter["schema"]
    if "$ref" in schema:
        schema_name = schema["$ref"].rsplit("/", 1)[-1]
        schema = openapi["components"]["schemas"][schema_name]
    assert set(schema["enum"]) == {"location_based", "market_based"}


def test_report_summary_discloses_both_methods_but_one_headline_total() -> None:
    totals = calculate_inventory_totals(ITEMS, Scope2HeadlineBasis.MARKET_BASED)
    summary = InventoryCalculationSummary(
        calculation_run_id=UUID("11111111-1111-1111-1111-111111111111"),
        inventory_id=UUID("22222222-2222-2222-2222-222222222222"),
        scope_2_headline_basis=Scope2HeadlineBasis.MARKET_BASED,
        scope_1_kg_co2e=totals["scope_1"],
        scope_2_location_based_kg_co2e=totals["scope_2_location_based"],
        scope_2_market_based_kg_co2e=totals["scope_2_market_based"],
        scope_3_kg_co2e=totals["scope_3"],
        total_kg_co2e=totals["headline_total"],
        total_t_co2e=totals["headline_total"] / Decimal("1000"),
        items=ITEMS,
    )

    payload = summary.model_dump(mode="json")
    assert payload["scope_2_headline_basis"] == "market_based"
    assert Decimal(payload["scope_2_location_based_kg_co2e"]) == Decimal("40")
    assert Decimal(payload["scope_2_market_based_kg_co2e"]) == Decimal("25")
    assert Decimal(payload["total_kg_co2e"]) == Decimal("425")
