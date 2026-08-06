from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

from app.models.activity import EmissionScope
from app.models.calculation import CalculationMethod
from app.services.data_review import _create_external_calculation_result


def test_external_result_is_not_factor_recalculated() -> None:
    tenant_id = UUID("11111111-1111-1111-1111-111111111111")
    run_id = UUID("22222222-2222-2222-2222-222222222222")
    activity_id = UUID("33333333-3333-3333-3333-333333333333")

    principal = SimpleNamespace(tenant_id=tenant_id)
    run = SimpleNamespace(id=run_id)
    activity = SimpleNamespace(id=activity_id)
    emission = SimpleNamespace(
        id=UUID("44444444-4444-4444-4444-444444444444"),
        external_calculation_id="data-calc-1",
        confirmed_scope_3_category=4,
        total_kg_co2e=Decimal("326.745"),
        co2_kg=Decimal("318.220"),
        ch4_kg_co2e=Decimal("2.115"),
        n2o_kg_co2e=Decimal("6.410"),
        methodology_version="DATa-2026.1",
        method_identifier="dcarbn.route.vehicle.v3",
        calculation_software_version="data-engine-3.4.0",
        external_activity_key="route-44-2026",
        uncertainty_percentage=Decimal("3.5"),
        comparison_inputs_json={
            "activity_value": "1250",
            "activity_unit": "tonne.km",
        },
        source_record_hash="abc123",
        source_record_version="3",
        calculated_at=datetime.now(UTC),
        lineage_json={"distance_source": "telematics"},
        data_quality_level="primary",
        data_quality_score=92,
    )

    result = _create_external_calculation_result(
        principal,
        run,
        activity,
        emission,
        EmissionScope.SCOPE_3,
    )

    assert result.method == CalculationMethod.EXTERNAL_OPERATIONAL_RESULT
    assert result.factor_value is None
    assert result.gross_kg_co2e == Decimal("326.745")
    assert (
        result.intermediate_values["method_identifier"]
        == "dcarbn.route.vehicle.v3"
    )
    assert (
        result.intermediate_values["calculation_software_version"]
        == "data-engine-3.4.0"
    )
    assert result.intermediate_values["comparison_inputs"] == {
        "activity_value": "1250",
        "activity_unit": "tonne.km",
    }
    assert result.allocated_kg_co2e == Decimal("326.745")
    assert "no emission factor reapplied" in result.calculation_formula
