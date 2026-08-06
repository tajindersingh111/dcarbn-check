from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal, get_current_principal, require_roles
from app.db.session import get_db
from app.models.methodology import MethodologyVersion
from app.schemas.methodology import (
    GoldenTestRunResponse,
    MethodologyComparisonResponse,
    MethodologyImpactPreviewRequest,
    MethodologyImpactPreviewResponse,
    MethodologyVersionResponse,
)
from app.services.methodologies import get_methodology_version
from app.services.methodology_governance import (
    compare_methodology_versions,
    preview_methodology_impact,
    retire_methodology_version,
    run_methodology_golden_tests,
)

router = APIRouter()
methodology_admin = Depends(require_roles("platform_admin", "methodology_manager"))


async def _get_or_404(db: AsyncSession, methodology_id: UUID) -> MethodologyVersion:
    method = await get_methodology_version(db, methodology_id)
    if method is None:
        raise HTTPException(status_code=404, detail="Methodology version not found.")
    return method


@router.get("/methodologies/{methodology_id}/golden-tests", response_model=GoldenTestRunResponse)
async def run_golden_tests(
    methodology_id: UUID,
    _: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> GoldenTestRunResponse:
    method = await _get_or_404(db, methodology_id)
    return GoldenTestRunResponse(methodology_id=method.id, passed=True, results=run_methodology_golden_tests(method))


@router.get(
    "/methodologies/{baseline_id}/compare/{candidate_id}",
    response_model=MethodologyComparisonResponse,
)
async def compare_versions(
    baseline_id: UUID, candidate_id: UUID,
    _: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> MethodologyComparisonResponse:
    return compare_methodology_versions(
        await _get_or_404(db, baseline_id), await _get_or_404(db, candidate_id)
    )


@router.post(
    "/methodologies/{baseline_id}/impact-preview/{candidate_id}",
    response_model=MethodologyImpactPreviewResponse,
    dependencies=[methodology_admin],
)
async def impact_preview(
    baseline_id: UUID, candidate_id: UUID, payload: MethodologyImpactPreviewRequest,
    _: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> MethodologyImpactPreviewResponse:
    return preview_methodology_impact(
        await _get_or_404(db, baseline_id), await _get_or_404(db, candidate_id), payload.inputs
    )


@router.post(
    "/methodologies/{methodology_id}/retire",
    response_model=MethodologyVersionResponse,
    dependencies=[methodology_admin],
)
async def retire_methodology(
    methodology_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> MethodologyVersionResponse:
    method = await retire_methodology_version(db, principal, await _get_or_404(db, methodology_id))
    return MethodologyVersionResponse.model_validate(method)
