from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal, get_current_principal
from app.db.session import get_db
from app.schemas.factor_resolution import (
    FactorResolutionRecordResponse,
    FactorResolutionRequest,
    FactorResolutionResponse,
    UnitNormalizationRequest,
    UnitNormalizationResponse,
)
from app.services.factor_resolution import (
    get_resolution_record,
    resolve_emission_factor,
)
from app.units.registry import UnitConversionError, get_unit_registry

router = APIRouter()


@router.post(
    "/units/normalize",
    response_model=UnitNormalizationResponse,
)
async def normalize_unit(
    payload: UnitNormalizationRequest,
    _: CurrentPrincipal = Depends(get_current_principal),
) -> UnitNormalizationResponse:
    registry = get_unit_registry()
    try:
        if payload.target_unit:
            converted = registry.convert(
                payload.value,
                payload.unit,
                payload.target_unit,
            )
            target = registry.resolve(payload.target_unit)
            source = registry.resolve(payload.unit)
            return UnitNormalizationResponse(
                original_value=payload.value,
                original_unit=payload.unit,
                normalized_value=converted,
                normalized_unit=target.canonical_name,
                dimension=source.dimension,
                conversion_multiplier=(
                    source.to_base_multiplier / target.to_base_multiplier
                ),
            )

        normalized = registry.normalize(payload.value, payload.unit)
        return UnitNormalizationResponse(
            original_value=normalized.original_value,
            original_unit=normalized.original_unit,
            normalized_value=normalized.normalized_value,
            normalized_unit=normalized.normalized_unit,
            dimension=normalized.dimension,
            conversion_multiplier=normalized.conversion_multiplier,
        )
    except UnitConversionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/emission-factors/resolve",
    response_model=FactorResolutionResponse,
)
async def resolve(
    payload: FactorResolutionRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> FactorResolutionResponse:
    return await resolve_emission_factor(db, principal, payload)


@router.get(
    "/factor-resolution-records/{resolution_record_id}",
    response_model=FactorResolutionRecordResponse,
)
async def get_record(
    resolution_record_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> FactorResolutionRecordResponse:
    record = await get_resolution_record(
        db,
        principal.tenant_id,
        resolution_record_id,
    )
    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Factor resolution record not found.",
        )
    return FactorResolutionRecordResponse.model_validate(record)
