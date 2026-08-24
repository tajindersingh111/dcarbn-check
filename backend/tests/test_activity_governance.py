from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.models.activity import ActivityType, EmissionScope
from app.models.inventory import Inventory, ReportingPeriod
from app.models.organisation import Organisation
from app.schemas.activity import ActivityCreate, ActivityUpdate
from app.services.activities import create_activity, update_activity
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
