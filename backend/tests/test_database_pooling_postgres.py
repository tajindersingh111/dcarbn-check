from __future__ import annotations

import os
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings
from app.db.pooling import (
    create_database_engine,
    create_operator_engine,
    create_session_factory,
)
from app.db.tenant_context import set_tenant_context

DATABASE_URL = os.environ.get("DATABASE_URL", "")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL.startswith("postgresql+asyncpg://"),
    reason="PostgreSQL pooled-connection validation requires PostgreSQL.",
)

TENANT_A = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
TENANT_B = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")


def postgres_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "test",
        "secret_key": "s" * 64,
        "mfa_encryption_key": "m" * 64,
        "database_url": DATABASE_URL,
        "database_connection_limit": 50,
        "database_api_replicas": 1,
        "database_api_pool_size": 1,
        "database_api_max_overflow": 0,
        "database_pool_timeout_seconds": 0.1,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture
async def pooled_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_database_engine(postgres_settings())
    organisation_a = uuid4()
    organisation_b = uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO tenants (id, name, slug, is_active, created_at, updated_at) "
                "VALUES "
                "(:tenant_a, 'Pool tenant A', :slug_a, true, now(), now()), "
                "(:tenant_b, 'Pool tenant B', :slug_b, true, now(), now()) "
                "ON CONFLICT (id) DO UPDATE SET updated_at = now()"
            ),
            {
                "tenant_a": TENANT_A,
                "tenant_b": TENANT_B,
                "slug_a": f"pool-a-{uuid4().hex}",
                "slug_b": f"pool-b-{uuid4().hex}",
            },
        )
        await connection.execute(
            text(
                "INSERT INTO organisations "
                "(id, tenant_id, name, country_code, is_active, created_at, updated_at) "
                "VALUES "
                "(:organisation_a, :tenant_a, 'Pool visible A', 'GB', true, now(), now()), "
                "(:organisation_b, :tenant_b, 'Pool visible B', 'GB', true, now(), now())"
            ),
            {
                "organisation_a": organisation_a,
                "organisation_b": organisation_b,
                "tenant_a": TENANT_A,
                "tenant_b": TENANT_B,
            },
        )
    try:
        yield engine
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM tenants WHERE id IN (:tenant_a, :tenant_b)"),
                {"tenant_a": TENANT_A, "tenant_b": TENANT_B},
            )
        await engine.dispose()


@pytest.mark.asyncio
async def test_tenant_context_is_reapplied_after_commit_and_pool_reuse(
    pooled_engine: AsyncEngine,
) -> None:
    configured = postgres_settings()
    sessions = create_session_factory(pooled_engine, configured)

    async with sessions() as session:
        await set_tenant_context(session, TENANT_A)
        first_backend = await session.scalar(text("SELECT pg_backend_pid()"))
        assert await session.scalar(text("SELECT count(*) FROM organisations")) == 1
        await session.commit()

        await set_tenant_context(session, TENANT_B)
        second_backend = await session.scalar(text("SELECT pg_backend_pid()"))
        assert await session.scalar(text("SELECT count(*) FROM organisations")) == 1
        assert first_backend == second_backend
        await session.commit()

    async with sessions() as session_without_tenant:
        assert (
            await session_without_tenant.scalar(
                text("SELECT count(*) FROM organisations")
            )
        ) == 0


@pytest.mark.asyncio
async def test_transaction_controls_survive_pgbouncer_compatible_mode(
    pooled_engine: AsyncEngine,
) -> None:
    configured = postgres_settings(database_pool_mode="pgbouncer_transaction")
    pgbouncer_compatible_engine = create_database_engine(configured)
    sessions = create_session_factory(pgbouncer_compatible_engine, configured)

    try:
        async with sessions() as session:
            await set_tenant_context(session, TENANT_A)
            values = await session.execute(
                text(
                    "SELECT current_setting('statement_timeout'), "
                    "current_setting('idle_in_transaction_session_timeout'), "
                    "current_setting('app.current_tenant_id')"
                )
            )
            statement_timeout, idle_timeout, tenant_id = values.one()
    finally:
        await pgbouncer_compatible_engine.dispose()

    assert statement_timeout == "30s"
    assert idle_timeout == "15s"
    assert tenant_id == str(TENANT_A)


@pytest.mark.asyncio
async def test_pool_exhaustion_respects_acquisition_timeout() -> None:
    engine = create_database_engine(postgres_settings())
    try:
        async with engine.connect():
            with pytest.raises(SQLAlchemyTimeoutError):
                async with engine.connect():
                    pytest.fail("Pool granted a connection beyond its budget.")
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_operator_pool_is_separate_bounded_and_exhaustible() -> None:
    configured = postgres_settings(database_operator_reserve=2)
    application_engine = create_database_engine(configured)
    operator_engine = create_operator_engine(configured)
    try:
        assert operator_engine is not application_engine
        assert operator_engine.sync_engine.pool is not application_engine.sync_engine.pool
        assert operator_engine.sync_engine.pool.size() == 2
        assert operator_engine.sync_engine.pool.overflow() <= 0

        async with operator_engine.connect() as first:
            async with operator_engine.connect() as second:
                first_backend = await first.scalar(text("SELECT pg_backend_pid()"))
                second_backend = await second.scalar(text("SELECT pg_backend_pid()"))
                assert first_backend != second_backend
                with pytest.raises(SQLAlchemyTimeoutError):
                    async with operator_engine.connect():
                        pytest.fail("Operator pool exceeded DATABASE_OPERATOR_RESERVE.")
    finally:
        await operator_engine.dispose()
        await application_engine.dispose()
