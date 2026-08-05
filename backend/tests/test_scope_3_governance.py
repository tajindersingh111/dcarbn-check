import pytest
from pydantic import ValidationError

from app.main import app
from app.models.inventory_governance import Scope3CategoryDispositionStatus
from app.schemas.scope3_governance import (
    Scope3CategoryDispositionInput,
    Scope3CategoryDispositionSet,
)


def _decision(category: int) -> Scope3CategoryDispositionInput:
    return Scope3CategoryDispositionInput(
        category=category,
        disposition=Scope3CategoryDispositionStatus.INCLUDED,
        rationale="Included after documented materiality screening.",
        evidence_reference=f"screening/category-{category}",
    )


def test_requires_exactly_one_decision_for_all_15_categories() -> None:
    payload = Scope3CategoryDispositionSet(
        items=[_decision(category) for category in range(1, 16)]
    )

    assert [item.category for item in payload.items] == list(range(1, 16))


def test_rejects_incomplete_category_set() -> None:
    with pytest.raises(ValidationError, match="at least 15 items"):
        Scope3CategoryDispositionSet(
            items=[_decision(category) for category in range(1, 15)]
        )


def test_rejects_duplicate_category_that_hides_an_omission() -> None:
    items = [_decision(category) for category in range(1, 16)]
    items[-1] = _decision(14)

    with pytest.raises(ValidationError, match="exactly one decision"):
        Scope3CategoryDispositionSet(items=items)


def test_excluded_category_requires_evidence_reference() -> None:
    with pytest.raises(ValidationError, match="evidence reference"):
        Scope3CategoryDispositionInput(
            category=4,
            disposition=Scope3CategoryDispositionStatus.EXCLUDED,
            rationale="Excluded after a documented relevance and materiality assessment.",
        )


def test_openapi_exposes_prepare_and_approval_routes() -> None:
    paths = app.openapi()["paths"]

    assert (
        "/api/v1/inventories/{inventory_id}/scope-3-category-dispositions"
        in paths
    )
    approval_path = (
        "/api/v1/inventories/{inventory_id}/"
        "scope-3-category-dispositions/approve"
    )
    assert approval_path in paths
    assert "post" in paths[approval_path]
