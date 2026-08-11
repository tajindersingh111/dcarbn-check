from __future__ import annotations

import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.environ.get("DATABASE_URL", "")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL.startswith("postgresql+asyncpg://"),
    reason="PostgreSQL RLS validation requires PostgreSQL.",
)

TENANT_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


@pytest.fixture
async def rls_engine():
    engine = create_async_engine(
        DATABASE_URL,
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
    )
    organisation_a = uuid4()
    organisation_b = uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO tenants (id, name, slug, is_active, created_at, updated_at) "
                "VALUES "
                "(:tenant_a, 'RLS tenant A', :slug_a, true, now(), now()), "
                "(:tenant_b, 'RLS tenant B', :slug_b, true, now(), now()) "
                "ON CONFLICT (id) DO UPDATE SET updated_at = now()"
            ),
            {
                "tenant_a": TENANT_A,
                "tenant_b": TENANT_B,
                "slug_a": f"rls-a-{uuid4().hex}",
                "slug_b": f"rls-b-{uuid4().hex}",
            },
        )
        await connection.execute(
            text(
                "INSERT INTO organisations "
                "(id, tenant_id, name, country_code, is_active, created_at, updated_at) "
                "VALUES "
                "(:organisation_a, :tenant_a, 'Visible A', 'GB', true, now(), now()), "
                "(:organisation_b, :tenant_b, 'Hidden B', 'GB', true, now(), now())"
            ),
            {
                "organisation_a": organisation_a,
                "organisation_b": organisation_b,
                "tenant_a": TENANT_A,
                "tenant_b": TENANT_B,
            },
        )
    try:
        yield engine, organisation_a, organisation_b
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM tenants WHERE id IN (:tenant_a, :tenant_b)"),
                {"tenant_a": TENANT_A, "tenant_b": TENANT_B},
            )
        await engine.dispose()


async def _enter_app_tenant(connection, tenant_id: UUID | None) -> None:
    await connection.execute(text("SET LOCAL ROLE dcarbn_app"))
    if tenant_id is not None:
        await connection.execute(
            text(
                "SELECT set_config("
                "'app.current_tenant_id', :tenant_id, true"
                ")"
            ),
            {"tenant_id": str(tenant_id)},
        )


@pytest.mark.asyncio
async def test_tenant_cannot_read_or_update_another_tenant(rls_engine) -> None:
    engine, organisation_a, organisation_b = rls_engine
    async with engine.connect() as connection:
        async with connection.begin():
            await _enter_app_tenant(connection, TENANT_A)
            visible = set(
                (
                    await connection.execute(
                        text(
                            "SELECT id FROM organisations "
                            "WHERE id IN (:organisation_a, :organisation_b)"
                        ),
                        {
                            "organisation_a": organisation_a,
                            "organisation_b": organisation_b,
                        },
                    )
                ).scalars()
            )
            changed = await connection.execute(
                text(
                    "UPDATE organisations SET name = 'cross-tenant attempt' "
                    "WHERE id = :organisation_b"
                ),
                {"organisation_b": organisation_b},
            )
    assert visible == {organisation_a}
    assert changed.rowcount == 0


@pytest.mark.asyncio
async def test_cross_tenant_insert_fails_closed(rls_engine) -> None:
    engine, _, _ = rls_engine
    async with engine.connect() as connection:
        with pytest.raises(DBAPIError):
            async with connection.begin():
                await _enter_app_tenant(connection, TENANT_A)
                await connection.execute(
                    text(
                        "INSERT INTO organisations "
                        "(id, tenant_id, name, country_code, is_active, created_at, updated_at) "
                        "VALUES (:id, :tenant_id, 'Forbidden', 'GB', true, now(), now())"
                    ),
                    {"id": uuid4(), "tenant_id": TENANT_B},
                )


@pytest.mark.asyncio
async def test_missing_context_and_pool_reuse_expose_no_rows(rls_engine) -> None:
    engine, _, _ = rls_engine
    async with engine.connect() as connection:
        async with connection.begin():
            await _enter_app_tenant(connection, TENANT_A)
            assert (
                await connection.scalar(text("SELECT count(*) FROM organisations"))
            ) == 1

    async with engine.connect() as reused_connection:
        async with reused_connection.begin():
            await _enter_app_tenant(reused_connection, None)
            assert (
                await reused_connection.scalar(
                    text("SELECT count(*) FROM organisations")
                )
            ) == 0


@pytest.mark.asyncio
async def test_rls_is_forced_and_auth_resolver_is_constrained(rls_engine) -> None:
    engine, _, _ = rls_engine
    async with engine.connect() as connection:
        forced = await connection.scalar(
            text(
                "SELECT relforcerowsecurity FROM pg_class "
                "WHERE relname = 'organisations'"
            )
        )
        async with connection.begin_nested():
            await connection.execute(text("SET LOCAL ROLE dcarbn_app"))
            resolved = await connection.scalar(
                text(
                    "SELECT public.dcarbn_resolve_auth_tenant("
                    "'refresh_session', :token_hash)"
                ),
                {"token_hash": "not-a-real-token-hash"},
            )
    assert forced is True
    assert resolved is None
