from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.models.organisation import Organisation
from app.schemas.organisation import OrganisationCreate, OrganisationUpdate
from app.services.audit import record_audit_event


async def create_organisation(
    db: AsyncSession,
    principal: CurrentPrincipal,
    payload: OrganisationCreate,
) -> Organisation:
    organisation = Organisation(
        tenant_id=principal.tenant_id,
        **payload.model_dump(),
    )
    db.add(organisation)
    await db.flush()

    await record_audit_event(
        db,
        principal,
        action="organisation.created",
        entity_type="organisation",
        entity_id=organisation.id,
        event_data={"name": organisation.name},
    )

    await db.commit()
    await db.refresh(organisation)
    return organisation


async def list_organisations(
    db: AsyncSession,
    tenant_id: UUID,
    limit: int,
    offset: int,
) -> tuple[list[Organisation], int]:
    query = (
        select(Organisation)
        .where(Organisation.tenant_id == tenant_id)
        .order_by(Organisation.name)
        .limit(limit)
        .offset(offset)
    )
    items = list((await db.scalars(query)).all())

    total_query = select(func.count()).select_from(Organisation).where(
        Organisation.tenant_id == tenant_id
    )
    total = int((await db.scalar(total_query)) or 0)
    return items, total


async def get_organisation(
    db: AsyncSession,
    tenant_id: UUID,
    organisation_id: UUID,
) -> Organisation | None:
    query = select(Organisation).where(
        Organisation.id == organisation_id,
        Organisation.tenant_id == tenant_id,
    )
    return await db.scalar(query)


async def update_organisation(
    db: AsyncSession,
    principal: CurrentPrincipal,
    organisation: Organisation,
    payload: OrganisationUpdate,
) -> Organisation:
    changes = payload.model_dump(exclude_unset=True)
    previous = {field: getattr(organisation, field) for field in changes}

    for field, value in changes.items():
        setattr(organisation, field, value)

    await record_audit_event(
        db,
        principal,
        action="organisation.updated",
        entity_type="organisation",
        entity_id=organisation.id,
        event_data={
            "previous": previous,
            "updated": changes,
        },
    )

    await db.commit()
    await db.refresh(organisation)
    return organisation
