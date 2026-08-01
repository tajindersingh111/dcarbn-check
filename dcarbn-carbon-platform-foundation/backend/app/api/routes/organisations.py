from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal, get_current_principal, require_roles
from app.db.session import get_db
from app.schemas.organisation import (
    OrganisationCreate,
    OrganisationListResponse,
    OrganisationResponse,
    OrganisationUpdate,
)
from app.services.organisations import (
    create_organisation,
    get_organisation,
    list_organisations,
    update_organisation,
)

router = APIRouter()


@router.post(
    "",
    response_model=OrganisationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("tenant_admin", "sustainability_manager"))],
)
async def create(
    payload: OrganisationCreate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> OrganisationResponse:
    organisation = await create_organisation(db, principal, payload)
    return OrganisationResponse.model_validate(organisation)


@router.get("", response_model=OrganisationListResponse)
async def list_all(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> OrganisationListResponse:
    items, total = await list_organisations(db, principal.tenant_id, limit, offset)
    return OrganisationListResponse(
        items=[OrganisationResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{organisation_id}", response_model=OrganisationResponse)
async def get_one(
    organisation_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> OrganisationResponse:
    organisation = await get_organisation(db, principal.tenant_id, organisation_id)
    if organisation is None:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    return OrganisationResponse.model_validate(organisation)


@router.patch(
    "/{organisation_id}",
    response_model=OrganisationResponse,
    dependencies=[Depends(require_roles("tenant_admin", "sustainability_manager"))],
)
async def update(
    organisation_id: UUID,
    payload: OrganisationUpdate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> OrganisationResponse:
    organisation = await get_organisation(db, principal.tenant_id, organisation_id)
    if organisation is None:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    updated = await update_organisation(db, principal, organisation, payload)
    return OrganisationResponse.model_validate(updated)
