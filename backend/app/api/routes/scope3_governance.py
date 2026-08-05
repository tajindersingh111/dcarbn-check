from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal, get_current_principal, require_roles
from app.db.session import get_db
from app.models.inventory_governance import Scope3CategoryDisposition
from app.schemas.scope3_governance import (
    Scope3CategoryDispositionListResponse,
    Scope3CategoryDispositionResponse,
    Scope3CategoryDispositionSet,
)
from app.services.scope3_governance import (
    approve_scope3_dispositions,
    list_scope3_dispositions,
    replace_scope3_dispositions,
)

router = APIRouter()
preparer = Depends(require_roles("tenant_admin", "sustainability_manager"))
approver = Depends(require_roles("tenant_admin", "inventory_approver"))


def _response(records: list[Scope3CategoryDisposition]) -> Scope3CategoryDispositionListResponse:
    items = [
        Scope3CategoryDispositionResponse.model_validate(record)
        for record in records
    ]
    return Scope3CategoryDispositionListResponse(
        items=items,
        total=len(items),
        complete=len(items) == 15,
        approved=(
            len(items) == 15
            and all(item.approved_by is not None for item in items)
        ),
    )


@router.get(
    "/inventories/{inventory_id}/scope-3-category-dispositions",
    response_model=Scope3CategoryDispositionListResponse,
)
async def get_dispositions(
    inventory_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> Scope3CategoryDispositionListResponse:
    records = await list_scope3_dispositions(
        db,
        principal.tenant_id,
        inventory_id,
    )
    return _response(records)


@router.put(
    "/inventories/{inventory_id}/scope-3-category-dispositions",
    response_model=Scope3CategoryDispositionListResponse,
    dependencies=[preparer],
)
async def put_dispositions(
    inventory_id: UUID,
    payload: Scope3CategoryDispositionSet,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> Scope3CategoryDispositionListResponse:
    records = await replace_scope3_dispositions(
        db,
        principal,
        inventory_id,
        payload,
    )
    return _response(records)


@router.post(
    "/inventories/{inventory_id}/scope-3-category-dispositions/approve",
    response_model=Scope3CategoryDispositionListResponse,
    dependencies=[approver],
)
async def approve_dispositions(
    inventory_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> Scope3CategoryDispositionListResponse:
    records = await approve_scope3_dispositions(
        db,
        principal,
        inventory_id,
    )
    return _response(records)
