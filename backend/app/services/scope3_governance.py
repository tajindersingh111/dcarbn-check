from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.models.inventory import Inventory, InventoryStatus
from app.models.inventory_governance import Scope3CategoryDisposition
from app.schemas.scope3_governance import Scope3CategoryDispositionSet
from app.services.audit import record_audit_event


async def list_scope3_dispositions(
    db: AsyncSession,
    tenant_id: UUID,
    inventory_id: UUID,
) -> list[Scope3CategoryDisposition]:
    await _get_inventory(db, tenant_id, inventory_id)
    query = (
        select(Scope3CategoryDisposition)
        .where(
            Scope3CategoryDisposition.tenant_id == tenant_id,
            Scope3CategoryDisposition.inventory_id == inventory_id,
        )
        .order_by(Scope3CategoryDisposition.category)
    )
    return list((await db.scalars(query)).all())


async def replace_scope3_dispositions(
    db: AsyncSession,
    principal: CurrentPrincipal,
    inventory_id: UUID,
    payload: Scope3CategoryDispositionSet,
) -> list[Scope3CategoryDisposition]:
    inventory = await _get_inventory(db, principal.tenant_id, inventory_id)
    if inventory.status in {
        InventoryStatus.APPROVED,
        InventoryStatus.LOCKED,
        InventoryStatus.SUPERSEDED,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Scope 3 dispositions cannot be changed after inventory approval.",
        )

    await db.execute(
        delete(Scope3CategoryDisposition).where(
            Scope3CategoryDisposition.inventory_id == inventory.id,
            Scope3CategoryDisposition.tenant_id == principal.tenant_id,
        )
    )
    now = datetime.now(UTC)
    records = [
        Scope3CategoryDisposition(
            tenant_id=principal.tenant_id,
            inventory_id=inventory.id,
            category=item.category,
            disposition=item.disposition,
            rationale=item.rationale,
            evidence_reference=item.evidence_reference,
            prepared_by=principal.subject,
            prepared_at=now,
            approved_by=None,
            approved_at=None,
        )
        for item in payload.items
    ]
    db.add_all(records)
    await db.flush()
    await record_audit_event(
        db,
        principal,
        action="scope_3.dispositions.prepared",
        entity_type="inventory",
        entity_id=inventory.id,
        event_data={
            "categories": [
                {
                    "category": item.category,
                    "disposition": item.disposition.value,
                }
                for item in payload.items
            ]
        },
    )
    await db.commit()
    for record in records:
        await db.refresh(record)
    return records


async def approve_scope3_dispositions(
    db: AsyncSession,
    principal: CurrentPrincipal,
    inventory_id: UUID,
) -> list[Scope3CategoryDisposition]:
    records = await list_scope3_dispositions(
        db,
        principal.tenant_id,
        inventory_id,
    )
    if len(records) != 15 or [item.category for item in records] != list(range(1, 16)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="All 15 Scope 3 category dispositions must be prepared.",
        )
    if any(item.prepared_by == principal.subject for item in records):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The preparer cannot approve their own Scope 3 dispositions.",
        )

    now = datetime.now(UTC)
    for record in records:
        record.approved_by = principal.subject
        record.approved_at = now
    await record_audit_event(
        db,
        principal,
        action="scope_3.dispositions.approved",
        entity_type="inventory",
        entity_id=inventory_id,
        event_data={"category_count": 15},
    )
    await db.commit()
    for record in records:
        await db.refresh(record)
    return records


async def scope3_dispositions_are_approved(
    db: AsyncSession,
    tenant_id: UUID,
    inventory_id: UUID,
) -> bool:
    records = await list_scope3_dispositions(db, tenant_id, inventory_id)
    return (
        len(records) == 15
        and [item.category for item in records] == list(range(1, 16))
        and all(item.approved_by is not None and item.approved_at is not None for item in records)
    )


def scope3_disposition_payload(
    records: list[Scope3CategoryDisposition],
) -> list[dict[str, object]]:
    return [
        {
            "category": item.category,
            "disposition": item.disposition.value,
            "rationale": item.rationale,
            "evidence_reference": item.evidence_reference,
            "prepared_by": item.prepared_by,
            "prepared_at": item.prepared_at.isoformat(),
            "approved_by": item.approved_by,
            "approved_at": item.approved_at.isoformat() if item.approved_at else None,
        }
        for item in records
    ]


async def _get_inventory(
    db: AsyncSession,
    tenant_id: UUID,
    inventory_id: UUID,
) -> Inventory:
    inventory = await db.scalar(
        select(Inventory).where(
            Inventory.id == inventory_id,
            Inventory.tenant_id == tenant_id,
        )
    )
    if inventory is None:
        raise HTTPException(status_code=404, detail="Inventory not found.")
    return inventory
