from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.accounting_connections import list_accounting_syncs


@pytest.mark.asyncio
async def test_sync_history_query_is_tenant_and_connection_scoped() -> None:
    db = AsyncMock(spec=AsyncSession)
    scalars = MagicMock()
    scalars.__iter__.return_value = iter([])
    db.scalars.return_value = scalars

    tenant_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    connection_id = UUID("77777777-7777-7777-7777-777777777777")

    assert await list_accounting_syncs(db, tenant_id, connection_id) == []

    statement = db.scalars.await_args.args[0]
    compiled = str(statement)
    assert "data_accounting_sync_jobs.tenant_id" in compiled
    assert "data_accounting_sync_jobs.connection_id" in compiled
    assert "ORDER BY data_accounting_sync_jobs.created_at DESC" in compiled


@pytest.mark.asyncio
async def test_tenant_sync_history_can_include_all_connections() -> None:
    db = AsyncMock(spec=AsyncSession)
    scalars = MagicMock()
    scalars.__iter__.return_value = iter([])
    db.scalars.return_value = scalars

    await list_accounting_syncs(
        db,
        UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
    )

    statement = str(db.scalars.await_args.args[0])
    assert "data_accounting_sync_jobs.tenant_id" in statement
    assert "data_accounting_sync_jobs.connection_id =" not in statement
