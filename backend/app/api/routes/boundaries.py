from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal, get_current_principal, require_roles
from app.db.session import get_db
from app.schemas.boundary import (
    BoundaryCreate,
    BoundaryListResponse,
    BoundaryResponse,
    BoundaryUpdate,
    MembershipCreate,
    MembershipListResponse,
    MembershipResponse,
    MembershipUpdate,
)
from app.services.boundaries import (
    approve_boundary,
    create_boundary,
    create_membership,
    get_boundary,
    get_membership,
    list_boundaries,
    list_memberships,
    update_boundary,
    update_membership,
)

router = APIRouter()
editor_roles = Depends(
    require_roles("tenant_admin", "sustainability_manager")
)
approver_roles = Depends(require_roles("tenant_admin", "inventory_approver"))


@router.post(
    "/reporting-periods/{reporting_period_id}/boundaries",
    response_model=BoundaryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[editor_roles],
)
async def create(
    reporting_period_id: UUID,
    payload: BoundaryCreate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> BoundaryResponse:
    boundary = await create_boundary(db, principal, reporting_period_id, payload)
    return BoundaryResponse.model_validate(boundary)


@router.get(
    "/reporting-periods/{reporting_period_id}/boundaries",
    response_model=BoundaryListResponse,
)
async def list_all(
    reporting_period_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> BoundaryListResponse:
    items = await list_boundaries(db, principal.tenant_id, reporting_period_id)
    return BoundaryListResponse(
        items=[BoundaryResponse.model_validate(item) for item in items],
        total=len(items),
    )


@router.get("/boundaries/{boundary_id}", response_model=BoundaryResponse)
async def get_one(
    boundary_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> BoundaryResponse:
    boundary = await get_boundary(db, principal.tenant_id, boundary_id)
    if boundary is None:
        raise HTTPException(status_code=404, detail="Boundary not found.")
    return BoundaryResponse.model_validate(boundary)


@router.patch(
    "/boundaries/{boundary_id}",
    response_model=BoundaryResponse,
    dependencies=[editor_roles],
)
async def update(
    boundary_id: UUID,
    payload: BoundaryUpdate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> BoundaryResponse:
    boundary = await get_boundary(db, principal.tenant_id, boundary_id)
    if boundary is None:
        raise HTTPException(status_code=404, detail="Boundary not found.")
    updated = await update_boundary(db, principal, boundary, payload)
    return BoundaryResponse.model_validate(updated)


@router.post(
    "/boundaries/{boundary_id}/approve",
    response_model=BoundaryResponse,
    dependencies=[approver_roles],
)
async def approve(
    boundary_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> BoundaryResponse:
    boundary = await get_boundary(db, principal.tenant_id, boundary_id)
    if boundary is None:
        raise HTTPException(status_code=404, detail="Boundary not found.")
    approved = await approve_boundary(db, principal, boundary)
    return BoundaryResponse.model_validate(approved)


@router.post(
    "/boundaries/{boundary_id}/members",
    response_model=MembershipResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[editor_roles],
)
async def add_member(
    boundary_id: UUID,
    payload: MembershipCreate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> MembershipResponse:
    boundary = await get_boundary(db, principal.tenant_id, boundary_id)
    if boundary is None:
        raise HTTPException(status_code=404, detail="Boundary not found.")
    membership = await create_membership(db, principal, boundary, payload)
    return MembershipResponse.model_validate(membership)


@router.get(
    "/boundaries/{boundary_id}/members",
    response_model=MembershipListResponse,
)
async def list_members(
    boundary_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> MembershipListResponse:
    boundary = await get_boundary(db, principal.tenant_id, boundary_id)
    if boundary is None:
        raise HTTPException(status_code=404, detail="Boundary not found.")
    items = await list_memberships(db, principal.tenant_id, boundary_id)
    return MembershipListResponse(
        items=[MembershipResponse.model_validate(item) for item in items],
        total=len(items),
    )


@router.patch(
    "/boundaries/{boundary_id}/members/{membership_id}",
    response_model=MembershipResponse,
    dependencies=[editor_roles],
)
async def update_member(
    boundary_id: UUID,
    membership_id: UUID,
    payload: MembershipUpdate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> MembershipResponse:
    boundary = await get_boundary(db, principal.tenant_id, boundary_id)
    if boundary is None:
        raise HTTPException(status_code=404, detail="Boundary not found.")
    membership = await get_membership(
        db,
        principal.tenant_id,
        boundary_id,
        membership_id,
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Boundary membership not found.")
    updated = await update_membership(
        db,
        principal,
        boundary,
        membership,
        payload,
    )
    return MembershipResponse.model_validate(updated)
