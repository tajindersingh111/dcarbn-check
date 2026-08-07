from uuid import UUID

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.models.organisation import Organisation
from app.schemas.workflows import ReportingPeriodCreate
from app.services.workflows import create_reporting_period
from tests.conftest import TEST_TENANT_ID

TEST_USER_ID = UUID("22222222-2222-2222-2222-222222222222")


def authenticated_principal() -> CurrentPrincipal:
    return CurrentPrincipal(
        subject=str(TEST_USER_ID),
        tenant_id=TEST_TENANT_ID,
        roles=frozenset({"tenant_admin"}),
    )


async def create_organisation(
    db_session: AsyncSession,
    name: str,
) -> Organisation:
    organisation = Organisation(
        tenant_id=TEST_TENANT_ID,
        name=name,
        country_code="GB",
    )
    db_session.add(organisation)
    await db_session.commit()
    await db_session.refresh(organisation)
    return organisation


def test_base_year_requires_reason_and_policy() -> None:
    with pytest.raises(ValidationError):
        ReportingPeriodCreate(
            organisation_id=UUID("33333333-3333-3333-3333-333333333333"),
            name="FY2025 base year",
            start_date="2025-01-01",
            end_date="2025-12-31",
            is_base_year=True,
        )


@pytest.mark.asyncio
async def test_governs_base_year_and_comparative_periods(
    db_session: AsyncSession,
) -> None:
    organisation = await create_organisation(db_session, "Governed Logistics")
    principal = authenticated_principal()

    base_year = await create_reporting_period(
        db_session,
        principal,
        ReportingPeriodCreate(
            organisation_id=organisation.id,
            name="FY2025 base year",
            start_date="2025-01-01",
            end_date="2025-12-31",
            is_base_year=True,
            base_year_reason="First complete assured organisational inventory.",
            recalculation_policy=(
                "Recalculate for structural changes or material errors meeting "
                "the significance threshold."
            ),
            recalculation_significance_threshold_percent="5.0",
        ),
    )
    assert base_year.is_base_year is True
    assert str(base_year.recalculation_significance_threshold_percent) == "5.0000"

    with pytest.raises(HTTPException) as duplicate_error:
        await create_reporting_period(
            db_session,
            principal,
            ReportingPeriodCreate(
                organisation_id=organisation.id,
                name="Alternative base year",
                start_date="2024-01-01",
                end_date="2024-12-31",
                is_base_year=True,
                base_year_reason="Alternative selection.",
                recalculation_policy="Five percent significance policy.",
            ),
        )
    assert duplicate_error.value.status_code == 409

    comparative = await create_reporting_period(
        db_session,
        principal,
        ReportingPeriodCreate(
            organisation_id=organisation.id,
            name="FY2026",
            start_date="2026-01-01",
            end_date="2026-12-31",
            comparative_reporting_period_id=base_year.id,
            recalculation_significance_threshold_percent="5.0",
        ),
    )
    assert comparative.comparative_reporting_period_id == base_year.id


@pytest.mark.asyncio
async def test_rejects_overlapping_comparative_period(
    db_session: AsyncSession,
) -> None:
    organisation = await create_organisation(db_session, "Comparison Controls")
    principal = authenticated_principal()
    earlier = await create_reporting_period(
        db_session,
        principal,
        ReportingPeriodCreate(
            organisation_id=organisation.id,
            name="Part year 2026",
            start_date="2026-01-01",
            end_date="2026-06-30",
        ),
    )

    with pytest.raises(HTTPException) as overlap_error:
        await create_reporting_period(
            db_session,
            principal,
            ReportingPeriodCreate(
                organisation_id=organisation.id,
                name="FY2026",
                start_date="2026-01-01",
                end_date="2026-12-31",
                comparative_reporting_period_id=earlier.id,
            ),
        )
    assert overlap_error.value.status_code == 422
