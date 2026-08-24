from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.models.emission_factor import (
    EmissionFactor,
    EmissionFactorSet,
    FactorSetStatus,
    GreenhouseGasComponent,
)
from app.services.emission_factors import approve_factor_set
from tests.conftest import TEST_TENANT_ID


@pytest.mark.asyncio
async def test_factor_importer_cannot_approve_own_factor_set(
    db_session: AsyncSession,
) -> None:
    factor_set = EmissionFactorSet(
        publisher="Department for Energy Security and Net Zero",
        dataset_name="UK Government GHG Conversion Factors for Company Reporting",
        dataset_version="2024-v1.1",
        reporting_year=2024,
        effective_from=date(2024, 1, 1),
        effective_to=date(2024, 12, 31),
        source_filename="ghg-conversion-factors-2024-FlatFormat_v1_1.xlsx",
        source_sha256="a" * 64,
        status=FactorSetStatus.DRAFT,
        imported_at=datetime.now(UTC),
        imported_by="factor-manager@example.com",
    )
    db_session.add(factor_set)
    await db_session.flush()
    db_session.add(
        EmissionFactor(
            factor_set_id=factor_set.id,
            source_factor_id="2_103_1036_8_1",
            scope="Scope 1",
            level_1="Bioenergy",
            level_2="Biofuel",
            level_3="Biodiesel HVO",
            activity_unit="litres",
            factor_unit_text="kg CO2e",
            greenhouse_gas_component=GreenhouseGasComponent.TOTAL_CO2E,
            greenhouse_gas_label="kg CO2e",
            factor_value=Decimal("0.03558"),
            factor_denominator_unit="litres",
            geography_code="GB",
            reporting_year=2024,
            lifecycle_boundary="direct",
            source_row_number=1,
            raw_source_data={"source": "official-workbook"},
        )
    )
    await db_session.commit()
    principal = CurrentPrincipal(
        subject="factor-manager@example.com",
        tenant_id=TEST_TENANT_ID,
        roles=frozenset({"factor_manager"}),
    )

    with pytest.raises(HTTPException, match="other than its importer") as exc_info:
        await approve_factor_set(
            db_session,
            principal,
            factor_set,
            "Reviewed against official publication",
        )

    assert exc_info.value.status_code == 409
    assert factor_set.status == FactorSetStatus.DRAFT
