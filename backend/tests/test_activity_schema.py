from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.models.activity import ActivityType, EmissionScope, Scope2Method
from app.schemas.activity import ActivityCreate


def base_payload() -> dict[str, object]:
    return {
        "organisation_id": UUID("11111111-1111-1111-1111-111111111111"),
        "activity_type": ActivityType.MOBILE_COMBUSTION,
        "scope": EmissionScope.SCOPE_1,
        "activity_date": date(2026, 1, 1),
        "description": "Distance travelled by owned Class I diesel van",
        "activity_value": Decimal("100"),
        "activity_unit": "km",
        "factor_level_1": "Delivery vehicles",
        "factor_level_2": "Vans",
        "factor_level_3": "Class I (up to 1.305 tonnes)",
        "factor_column_text": "Diesel",
        "source_record_id": "fleet-distance-001",
        "metadata_json": {
            "calculation_method_id": (
                "scope1.mobile_combustion.delivery_van.class1.diesel.km.uk_2026.v1"
            )
        },
    }


def test_accepts_scope_1_activity() -> None:
    activity = ActivityCreate.model_validate(base_payload())

    assert activity.scope == EmissionScope.SCOPE_1


def test_requires_category_for_scope_3() -> None:
    payload = base_payload()
    payload["scope"] = EmissionScope.SCOPE_3
    payload["activity_type"] = ActivityType.FREIGHT_TRANSPORT

    with pytest.raises(ValidationError):
        ActivityCreate.model_validate(payload)


def test_requires_method_for_scope_2() -> None:
    payload = base_payload()
    payload["scope"] = EmissionScope.SCOPE_2
    payload["activity_type"] = ActivityType.PURCHASED_ELECTRICITY
    payload["scope_2_method"] = Scope2Method.NOT_APPLICABLE

    with pytest.raises(ValidationError):
        ActivityCreate.model_validate(payload)
