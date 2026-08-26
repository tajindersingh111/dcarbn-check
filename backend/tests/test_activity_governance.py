from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal, get_current_principal
from app.main import app
from app.models.activity import ActivityRecord, ActivityType, EmissionScope
from app.models.inventory import Inventory, ReportingPeriod
from app.models.organisation import Organisation
from app.schemas.activity import ActivityCreate, ActivityUpdate
from app.services.activities import create_activity, create_activity_batch, update_activity
from tests.conftest import TEST_TENANT_ID


async def _inventory(
    db_session: AsyncSession,
    *,
    organisation_name: str,
    inventory_name: str,
) -> tuple[Organisation, Inventory]:
    organisation = Organisation(
        tenant_id=TEST_TENANT_ID,
        name=organisation_name,
        country_code="GB",
    )
    db_session.add(organisation)
    await db_session.flush()
    period = ReportingPeriod(
        tenant_id=TEST_TENANT_ID,
        organisation_id=organisation.id,
        name="Calendar 2024",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )
    db_session.add(period)
    await db_session.flush()
    inventory = Inventory(
        tenant_id=TEST_TENANT_ID,
        reporting_period_id=period.id,
        name=inventory_name,
    )
    db_session.add(inventory)
    await db_session.commit()
    return organisation, inventory


def _hvo_payload(
    organisation: Organisation,
    *,
    source_record_id: str = "hvo-source-001",
) -> ActivityCreate:
    return ActivityCreate(
        organisation_id=organisation.id,
        activity_type=ActivityType.MOBILE_COMBUSTION,
        scope=EmissionScope.SCOPE_1,
        activity_date=date(2024, 6, 30),
        description="Evidenced HVO fuel",
        activity_value=Decimal("100"),
        activity_unit="litres",
        factor_level_1="Bioenergy",
        factor_level_2="Biofuel",
        factor_level_3="Biodiesel HVO",
        lifecycle_boundary="direct",
        source_system="csv-upload",
        source_record_id=source_record_id,
        evidence_reference="hvo-invoice.pdf",
        metadata_json={"calculation_method_id": "scope1.mobile_combustion.hvo.litres.uk_2024.v1"},
    )


def _principal() -> CurrentPrincipal:
    return CurrentPrincipal(
        subject="reviewer@example.com",
        tenant_id=TEST_TENANT_ID,
        roles=frozenset({"sustainability_manager"}),
    )


@pytest.mark.asyncio
async def test_activity_organisation_must_match_inventory_period(
    db_session: AsyncSession,
) -> None:
    _, inventory = await _inventory(
        db_session,
        organisation_name="Inventory owner",
        inventory_name="Owner inventory",
    )
    other_organisation, _ = await _inventory(
        db_session,
        organisation_name="Other organisation",
        inventory_name="Other inventory",
    )

    with pytest.raises(HTTPException, match="must match") as exc_info:
        await create_activity(
            db_session,
            _principal(),
            inventory.id,
            _hvo_payload(other_organisation),
        )

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_source_record_cannot_supersede_another_organisation(
    db_session: AsyncSession,
) -> None:
    first_organisation, first_inventory = await _inventory(
        db_session,
        organisation_name="First organisation",
        inventory_name="First inventory",
    )
    second_organisation, second_inventory = await _inventory(
        db_session,
        organisation_name="Second organisation",
        inventory_name="Second inventory",
    )
    await create_activity(
        db_session,
        _principal(),
        first_inventory.id,
        _hvo_payload(first_organisation, source_record_id="shared-source-id"),
    )

    with pytest.raises(HTTPException, match="another inventory or organisation") as exc_info:
        await create_activity(
            db_session,
            _principal(),
            second_inventory.id,
            _hvo_payload(second_organisation, source_record_id="shared-source-id"),
        )

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_hvo_evidence_cannot_be_removed_by_update(
    db_session: AsyncSession,
) -> None:
    organisation, inventory = await _inventory(
        db_session,
        organisation_name="HVO organisation",
        inventory_name="HVO inventory",
    )
    activity = await create_activity(
        db_session,
        _principal(),
        inventory.id,
        _hvo_payload(organisation),
    )

    with pytest.raises(HTTPException, match="requires evidence") as exc_info:
        await update_activity(
            db_session,
            _principal(),
            activity,
            ActivityUpdate(evidence_reference=None),
        )

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_activity_batch_commits_every_record_together(
    db_session: AsyncSession,
) -> None:
    organisation, inventory = await _inventory(
        db_session,
        organisation_name="Batch organisation",
        inventory_name="Batch inventory",
    )

    activities = await create_activity_batch(
        db_session,
        _principal(),
        inventory.id,
        [
            _hvo_payload(organisation, source_record_id="batch-source-001"),
            _hvo_payload(organisation, source_record_id="batch-source-002"),
        ],
    )

    assert len(activities) == 2
    count = await db_session.scalar(
        select(func.count())
        .select_from(ActivityRecord)
        .where(ActivityRecord.inventory_id == inventory.id)
    )
    assert count == 2


@pytest.mark.asyncio
async def test_activity_batch_rejects_duplicate_source_identity_without_writes(
    db_session: AsyncSession,
) -> None:
    organisation, inventory = await _inventory(
        db_session,
        organisation_name="Duplicate batch organisation",
        inventory_name="Duplicate batch inventory",
    )

    with pytest.raises(HTTPException, match="must be unique") as exc_info:
        await create_activity_batch(
            db_session,
            _principal(),
            inventory.id,
            [
                _hvo_payload(organisation, source_record_id="duplicate-source"),
                _hvo_payload(organisation, source_record_id="duplicate-source"),
            ],
        )

    assert exc_info.value.status_code == 422
    count = await db_session.scalar(
        select(func.count())
        .select_from(ActivityRecord)
        .where(ActivityRecord.inventory_id == inventory.id)
    )
    assert count == 0


@pytest.mark.asyncio
async def test_activity_batch_rolls_back_all_records_when_one_conflicts(
    db_session: AsyncSession,
) -> None:
    first_organisation, first_inventory = await _inventory(
        db_session,
        organisation_name="Existing source organisation",
        inventory_name="Existing source inventory",
    )
    second_organisation, second_inventory = await _inventory(
        db_session,
        organisation_name="Import target organisation",
        inventory_name="Import target inventory",
    )
    await create_activity(
        db_session,
        _principal(),
        first_inventory.id,
        _hvo_payload(first_organisation, source_record_id="conflicting-source"),
    )
    first_inventory_id = first_inventory.id
    second_inventory_id = second_inventory.id

    with pytest.raises(HTTPException, match="another inventory or organisation"):
        await create_activity_batch(
            db_session,
            _principal(),
            second_inventory_id,
            [
                _hvo_payload(second_organisation, source_record_id="would-be-partial"),
                _hvo_payload(second_organisation, source_record_id="conflicting-source"),
            ],
        )

    rolled_back_count = await db_session.scalar(
        select(func.count())
        .select_from(ActivityRecord)
        .where(
            ActivityRecord.inventory_id == second_inventory_id,
            ActivityRecord.source_record_id == "would-be-partial",
        )
    )
    existing_count = await db_session.scalar(
        select(func.count())
        .select_from(ActivityRecord)
        .where(
            ActivityRecord.inventory_id == first_inventory_id,
            ActivityRecord.source_record_id == "conflicting-source",
            ActivityRecord.is_current.is_(True),
        )
    )
    assert rolled_back_count == 0
    assert existing_count == 1


@pytest.mark.asyncio
async def test_activity_batch_api_returns_one_atomic_result(
    db_session: AsyncSession,
    client: AsyncClient,
) -> None:
    organisation, inventory = await _inventory(
        db_session,
        organisation_name="API batch organisation",
        inventory_name="API batch inventory",
    )
    app.dependency_overrides[get_current_principal] = _principal

    response = await client.post(
        f"/api/v1/inventories/{inventory.id}/activities/batch",
        json={
            "items": [
                _hvo_payload(
                    organisation,
                    source_record_id="api-batch-source-001",
                ).model_dump(mode="json"),
                _hvo_payload(
                    organisation,
                    source_record_id="api-batch-source-002",
                ).model_dump(mode="json"),
            ]
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["total"] == 2
    assert len(response.json()["items"]) == 2
