from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal, get_current_principal, require_roles
from app.db.session import get_db
from app.models.methodology import MethodologyStatus, MethodologyVersion
from app.schemas.methodology import (
    MethodologyVersionCreate,
    MethodologyVersionListResponse,
    MethodologyVersionResponse,
)
from app.services.methodologies import (
    activate_methodology_version,
    approve_methodology_version,
    create_methodology_version,
    get_methodology_version,
    list_methodology_versions,
    review_methodology_version,
    submit_methodology_version,
)

router = APIRouter()
methodology_admin = Depends(
    require_roles("platform_admin", "methodology_manager")
)


@router.post(
    "/methodologies",
    response_model=MethodologyVersionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[methodology_admin],
)
async def create_methodology(
    payload: MethodologyVersionCreate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> MethodologyVersionResponse:
    method = await create_methodology_version(db, principal, payload)
    return MethodologyVersionResponse.model_validate(method)


@router.get(
    "/methodologies",
    response_model=MethodologyVersionListResponse,
)
async def list_methodologies(
    method_key: str | None = Query(default=None, max_length=250),
    status_filter: MethodologyStatus | None = Query(default=None, alias="status"),
    _: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> MethodologyVersionListResponse:
    items = await list_methodology_versions(
        db,
        method_key=method_key,
        status_filter=status_filter,
    )
    return MethodologyVersionListResponse(
        items=[
            MethodologyVersionResponse.model_validate(item)
            for item in items
        ],
        total=len(items),
    )


@router.get(
    "/methodologies/{methodology_id}",
    response_model=MethodologyVersionResponse,
)
async def get_methodology(
    methodology_id: UUID,
    _: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> MethodologyVersionResponse:
    return MethodologyVersionResponse.model_validate(
        await _get_or_404(db, methodology_id)
    )


@router.post(
    "/methodologies/{methodology_id}/submit",
    response_model=MethodologyVersionResponse,
    dependencies=[methodology_admin],
)
async def submit_methodology(
    methodology_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> MethodologyVersionResponse:
    method = await submit_methodology_version(
        db,
        principal,
        await _get_or_404(db, methodology_id),
    )
    return MethodologyVersionResponse.model_validate(method)


@router.post(
    "/methodologies/{methodology_id}/review",
    response_model=MethodologyVersionResponse,
    dependencies=[methodology_admin],
)
async def review_methodology(
    methodology_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> MethodologyVersionResponse:
    method = await review_methodology_version(
        db,
        principal,
        await _get_or_404(db, methodology_id),
    )
    return MethodologyVersionResponse.model_validate(method)


@router.post(
    "/methodologies/{methodology_id}/approve",
    response_model=MethodologyVersionResponse,
    dependencies=[methodology_admin],
)
async def approve_methodology(
    methodology_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> MethodologyVersionResponse:
    method = await approve_methodology_version(
        db,
        principal,
        await _get_or_404(db, methodology_id),
    )
    return MethodologyVersionResponse.model_validate(method)


@router.post(
    "/methodologies/{methodology_id}/activate",
    response_model=MethodologyVersionResponse,
    dependencies=[methodology_admin],
)
async def activate_methodology(
    methodology_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> MethodologyVersionResponse:
    method = await activate_methodology_version(
        db,
        principal,
        await _get_or_404(db, methodology_id),
    )
    return MethodologyVersionResponse.model_validate(method)


async def _get_or_404(
    db: AsyncSession,
    methodology_id: UUID,
) -> MethodologyVersion:
    method = await get_methodology_version(db, methodology_id)
    if method is None:
        raise HTTPException(status_code=404, detail="Methodology version not found.")
    return method
