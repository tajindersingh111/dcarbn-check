from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.pagination import CursorPosition
from app.auth.dependencies import CurrentPrincipal
from app.integrations.data.accounting_connectors import (
    AccountingProvider,
    MappingProfile,
    SyncRequest,
    redact_connector_diagnostics,
)
from app.integrations.data.accounting_scope3 import REQUIRED_COLUMNS
from app.models.data_integration import (
    DataAccountingConnection,
    DataAccountingSyncJob,
)
from app.models.organisation import Organisation
from app.schemas.data_integration import (
    DataAccountingConnectionCreate,
    DataAccountingSyncCreate,
)
from app.services.audit import record_audit_event


async def upsert_accounting_connection(
    db: AsyncSession,
    principal: CurrentPrincipal,
    payload: DataAccountingConnectionCreate,
) -> DataAccountingConnection:
    organisation = await db.scalar(
        select(Organisation).where(
            Organisation.id == payload.organisation_id,
            Organisation.tenant_id == principal.tenant_id,
        )
    )
    if organisation is None:
        raise HTTPException(status_code=404, detail="Organisation not found.")

    provider = AccountingProvider(payload.provider.value)
    MappingProfile(
        provider=provider,
        version=payload.mapping_profile_version,
        mappings=payload.mapping,
    ).validate(REQUIRED_COLUMNS)

    existing = await db.scalar(
        select(DataAccountingConnection).where(
            DataAccountingConnection.tenant_id == principal.tenant_id,
            DataAccountingConnection.provider == provider.value,
            DataAccountingConnection.external_company_id
            == payload.external_company_id,
        )
    )
    values = payload.model_dump(exclude={"mapping", "provider"})
    if existing is None:
        connection = DataAccountingConnection(
            tenant_id=principal.tenant_id,
            provider=provider.value,
            mapping_json=payload.mapping,
            status="draft",
            **values,
        )
        db.add(connection)
        await db.flush()
    else:
        connection = existing
        for field, value in values.items():
            setattr(connection, field, value)
        connection.mapping_json = payload.mapping
        if connection.status == "revoked":
            connection.status = "draft"

    await record_audit_event(
        db,
        principal,
        action="data.accounting_connection.upserted",
        entity_type="data_accounting_connection",
        entity_id=connection.id,
        event_data={
            "provider": connection.provider,
            "external_company_id": connection.external_company_id,
            "mapping_profile_version": connection.mapping_profile_version,
            "status": connection.status,
        },
    )
    await db.commit()
    await db.refresh(connection)
    return connection


async def list_accounting_connections(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    limit: int = 50,
) -> list[DataAccountingConnection]:
    items = await db.scalars(
        select(DataAccountingConnection)
        .where(DataAccountingConnection.tenant_id == tenant_id)
        .order_by(
            DataAccountingConnection.created_at.desc(),
            DataAccountingConnection.id.desc(),
        )
        .limit(limit)
    )
    return list(items)


async def list_accounting_syncs(
    db: AsyncSession,
    tenant_id: UUID,
    connection_id: UUID | None = None,
    *,
    limit: int = 50,
    cursor: CursorPosition | None = None,
) -> tuple[list[DataAccountingSyncJob], CursorPosition | None]:
    statement = select(DataAccountingSyncJob).where(
        DataAccountingSyncJob.tenant_id == tenant_id
    )
    if connection_id is not None:
        statement = statement.where(
            DataAccountingSyncJob.connection_id == connection_id
        )
    if cursor is not None:
        statement = statement.where(
            or_(
                DataAccountingSyncJob.created_at < cursor.created_at,
                and_(
                    DataAccountingSyncJob.created_at == cursor.created_at,
                    DataAccountingSyncJob.id < cursor.id,
                ),
            )
        )

    rows = list(
        (
            await db.scalars(
                statement.order_by(
                    DataAccountingSyncJob.created_at.desc(),
                    DataAccountingSyncJob.id.desc(),
                ).limit(limit + 1)
            )
        ).all()
    )
    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = (
        CursorPosition(created_at=items[-1].created_at, id=items[-1].id)
        if has_more and items
        else None
    )
    return items, next_cursor


async def create_accounting_sync(
    db: AsyncSession,
    principal: CurrentPrincipal,
    connection_id: UUID,
    payload: DataAccountingSyncCreate,
) -> DataAccountingSyncJob:
    connection = await db.scalar(
        select(DataAccountingConnection).where(
            DataAccountingConnection.id == connection_id,
            DataAccountingConnection.tenant_id == principal.tenant_id,
        )
    )
    if connection is None:
        raise HTTPException(status_code=404, detail="Accounting connection not found.")
    if connection.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only an active accounting connection can be synchronised.",
        )

    request = SyncRequest(
        tenant_id=str(principal.tenant_id),
        external_customer_id=connection.external_customer_id,
        provider=AccountingProvider(connection.provider),
        external_company_id=connection.external_company_id,
        mapping_profile_version=connection.mapping_profile_version,
        cursor=payload.cursor,
        requested_from=payload.requested_from,
        requested_to=payload.requested_to,
    )
    existing = await db.scalar(
        select(DataAccountingSyncJob).where(
            DataAccountingSyncJob.tenant_id == principal.tenant_id,
            DataAccountingSyncJob.sync_identity == request.sync_identity,
        )
    )
    if existing is not None:
        return existing

    job = DataAccountingSyncJob(
        tenant_id=principal.tenant_id,
        connection_id=connection.id,
        sync_identity=request.sync_identity,
        cursor_before=payload.cursor,
        requested_from=payload.requested_from,
        requested_to=payload.requested_to,
        status="queued",
        requested_by=principal.subject,
        started_at=datetime.now(UTC),
        diagnostics_json=redact_connector_diagnostics(
            {
                "provider": connection.provider,
                "external_company_id": connection.external_company_id,
                "mapping_profile_version": connection.mapping_profile_version,
            }
        ),
    )
    db.add(job)
    await db.flush()
    await record_audit_event(
        db,
        principal,
        action="data.accounting_sync.queued",
        entity_type="data_accounting_sync_job",
        entity_id=job.id,
        event_data={
            "connection_id": str(connection.id),
            "provider": connection.provider,
            "sync_identity": job.sync_identity,
        },
    )
    await db.commit()
    await db.refresh(job)
    return job
