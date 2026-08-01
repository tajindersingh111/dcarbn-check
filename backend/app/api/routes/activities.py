from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal, get_current_principal, require_roles
from app.db.session import get_db
from app.schemas.activity import (
    ActivityCreate,
    ActivityListResponse,
    ActivityResponse,
    ActivityUpdate,
)
from app.services.activities import (
    create_activity,
    get_activity,
    list_activities,
    update_activity,
)

router = APIRouter()
editor = Depends(require_roles("tenant_admin", "sustainability_manager", "data_contributor"))


@router.post(
    "/inventories/{inventory_id}/activities",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[editor],
)
async def create(
    inventory_id: UUID,
    payload: ActivityCreate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> ActivityResponse:
    activity = await create_activity(db, principal, inventory_id, payload)
    return ActivityResponse.model_validate(activity)


@router.get(
    "/inventories/{inventory_id}/activities",
    response_model=ActivityListResponse,
)
async def list_all(
    inventory_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> ActivityListResponse:
    items, total = await list_activities(
        db,
        principal.tenant_id,
        inventory_id,
        limit,
        offset,
    )
    return ActivityListResponse(
        items=[ActivityResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/activities/{activity_id}", response_model=ActivityResponse)
async def get_one(
    activity_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> ActivityResponse:
    activity = await get_activity(db, principal.tenant_id, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found.")
    return ActivityResponse.model_validate(activity)


@router.patch(
    "/activities/{activity_id}",
    response_model=ActivityResponse,
    dependencies=[editor],
)
async def update(
    activity_id: UUID,
    payload: ActivityUpdate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> ActivityResponse:
    activity = await get_activity(db, principal.tenant_id, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found.")
    updated = await update_activity(db, principal, activity, payload)
    return ActivityResponse.model_validate(updated)
