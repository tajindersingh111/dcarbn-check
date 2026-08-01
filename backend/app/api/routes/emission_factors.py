from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal, get_current_principal, require_roles
from app.db.session import get_db
from app.models.emission_factor import FactorSetStatus, GreenhouseGasComponent
from app.schemas.emission_factor import (
    EmissionFactorListResponse,
    EmissionFactorResponse,
    FactorImportErrorResponse,
    FactorImportJobResponse,
    FactorSetApprovalRequest,
    FactorSetImportMetadata,
    FactorSetListResponse,
    FactorSetResponse,
    FactorSetSupersedeRequest,
)
from app.services.emission_factors import (
    approve_factor_set,
    get_factor_set,
    get_import_job,
    import_uk_2026_factor_workbook,
    list_factor_sets,
    list_import_errors,
    search_factors,
    supersede_factor_set,
)

router = APIRouter()
factor_admin = Depends(require_roles("platform_admin", "factor_manager"))


@router.post(
    "/emission-factor-sets/import/uk-2026",
    response_model=FactorImportJobResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[factor_admin],
)
async def import_uk_2026(
    metadata_json: str = Form(...),
    workbook: UploadFile = File(...),
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> FactorImportJobResponse:
    try:
        metadata = FactorSetImportMetadata.model_validate(
            json.loads(metadata_json)
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid metadata_json: {exc}",
        ) from exc

    job = await import_uk_2026_factor_workbook(
        db,
        principal,
        workbook,
        metadata,
    )
    return FactorImportJobResponse.model_validate(job)


@router.get(
    "/emission-factor-sets",
    response_model=FactorSetListResponse,
)
async def list_sets(
    status_filter: FactorSetStatus | None = Query(default=None, alias="status"),
    reporting_year: int | None = Query(default=None, ge=1990, le=2200),
    _: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> FactorSetListResponse:
    items = await list_factor_sets(
        db,
        status_filter=status_filter,
        reporting_year=reporting_year,
    )
    return FactorSetListResponse(
        items=[FactorSetResponse.model_validate(item) for item in items],
        total=len(items),
    )


@router.get(
    "/emission-factor-sets/{factor_set_id}",
    response_model=FactorSetResponse,
)
async def get_set(
    factor_set_id: UUID,
    _: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> FactorSetResponse:
    factor_set = await get_factor_set(db, factor_set_id)
    if factor_set is None:
        raise HTTPException(status_code=404, detail="Factor set not found.")
    return FactorSetResponse.model_validate(factor_set)


@router.post(
    "/emission-factor-sets/{factor_set_id}/approve",
    response_model=FactorSetResponse,
    dependencies=[factor_admin],
)
async def approve_set(
    factor_set_id: UUID,
    payload: FactorSetApprovalRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> FactorSetResponse:
    factor_set = await get_factor_set(db, factor_set_id)
    if factor_set is None:
        raise HTTPException(status_code=404, detail="Factor set not found.")
    approved = await approve_factor_set(
        db,
        principal,
        factor_set,
        payload.reason,
    )
    return FactorSetResponse.model_validate(approved)


@router.post(
    "/emission-factor-sets/{factor_set_id}/supersede",
    response_model=FactorSetResponse,
    dependencies=[factor_admin],
)
async def supersede_set(
    factor_set_id: UUID,
    payload: FactorSetSupersedeRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> FactorSetResponse:
    factor_set = await get_factor_set(db, factor_set_id)
    replacement = await get_factor_set(db, payload.replacement_factor_set_id)
    if factor_set is None or replacement is None:
        raise HTTPException(status_code=404, detail="Factor set not found.")
    superseded = await supersede_factor_set(
        db,
        principal,
        factor_set,
        replacement,
        payload.reason,
    )
    return FactorSetResponse.model_validate(superseded)


@router.get(
    "/factor-import-jobs/{import_job_id}",
    response_model=FactorImportJobResponse,
)
async def get_job(
    import_job_id: UUID,
    _: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> FactorImportJobResponse:
    job = await get_import_job(db, import_job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Import job not found.")
    return FactorImportJobResponse.model_validate(job)


@router.get(
    "/factor-import-jobs/{import_job_id}/errors",
    response_model=list[FactorImportErrorResponse],
)
async def get_job_errors(
    import_job_id: UUID,
    _: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> list[FactorImportErrorResponse]:
    job = await get_import_job(db, import_job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Import job not found.")
    errors = await list_import_errors(db, import_job_id)
    return [
        FactorImportErrorResponse.model_validate(error)
        for error in errors
    ]


@router.get(
    "/emission-factors",
    response_model=EmissionFactorListResponse,
)
async def list_factors(
    q: str | None = Query(default=None, max_length=250),
    factor_set_id: UUID | None = None,
    reporting_year: int | None = Query(default=None, ge=1990, le=2200),
    scope: str | None = Query(default=None, max_length=50),
    level_1: str | None = Query(default=None, max_length=250),
    activity_unit: str | None = Query(default=None, max_length=100),
    component: GreenhouseGasComponent | None = None,
    approved_only: bool = True,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> EmissionFactorListResponse:
    items, total = await search_factors(
        db,
        query_text=q,
        factor_set_id=factor_set_id,
        reporting_year=reporting_year,
        scope=scope,
        level_1=level_1,
        activity_unit=activity_unit,
        component=component,
        approved_only=approved_only,
        limit=limit,
        offset=offset,
    )
    return EmissionFactorListResponse(
        items=[EmissionFactorResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )
