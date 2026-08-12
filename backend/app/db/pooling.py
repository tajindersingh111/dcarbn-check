from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import Connection, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, SessionTransaction
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.db.connection_budget import DatabaseConnectionBudget
from app.db.pool_metrics import configure_pool_metrics

_ROLE_PATTERN = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


class TenantGuardedSession(Session):
    """Synchronous session boundary used by SQLAlchemy's async adapter."""


@event.listens_for(TenantGuardedSession, "after_begin")
def apply_transaction_controls(
    session: Session,
    transaction: SessionTransaction,
    connection: Connection,
) -> None:
    if connection.dialect.name != "postgresql":
        return

    role_value = session.info.get("database_application_role")
    if not isinstance(role_value, str) or not _ROLE_PATTERN.fullmatch(role_value):
        raise ValueError("Database application role is invalid.")
    connection.exec_driver_sql(f'SET LOCAL ROLE "{role_value}"')

    statement_timeout = session.info.get("statement_timeout_ms")
    idle_timeout = session.info.get("idle_transaction_timeout_ms")
    if not isinstance(statement_timeout, int) or not isinstance(idle_timeout, int):
        raise ValueError("Database transaction timeouts are invalid.")
    connection.execute(
        text(
            "SELECT "
            "set_config('statement_timeout', :statement_timeout, true), "
            "set_config('idle_in_transaction_session_timeout', :idle_timeout, true)"
        ),
        {
            "statement_timeout": f"{statement_timeout}ms",
            "idle_timeout": f"{idle_timeout}ms",
        },
    )

    tenant_value = session.info.get("tenant_id")
    if tenant_value is not None:
        if not isinstance(tenant_value, UUID):
            raise ValueError("Database tenant context is invalid.")
        connection.execute(
            text(
                "SELECT set_config("
                "'app.current_tenant_id', :tenant_id, true"
                ")"
            ),
            {"tenant_id": str(tenant_value)},
        )


def database_budget(settings: Settings) -> DatabaseConnectionBudget:
    return DatabaseConnectionBudget(
        connection_limit=settings.database_connection_limit,
        safety_margin_percent=settings.database_safety_margin_percent,
        operator_reserve=settings.database_operator_reserve,
        monitoring_connections=settings.database_monitoring_connections,
        migration_connections=settings.database_migration_connections,
        api_replicas=settings.database_api_replicas,
        api_pool_size=settings.database_api_pool_size,
        api_max_overflow=settings.database_api_max_overflow,
        worker_replicas=settings.database_worker_replicas,
        worker_pool_size=settings.database_worker_pool_size,
        worker_max_overflow=settings.database_worker_max_overflow,
    )


def create_database_engine(settings: Settings) -> AsyncEngine:
    budget = database_budget(settings)
    budget.validate()
    backend = make_url(settings.database_url).get_backend_name()
    if backend != "postgresql":
        return create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
        )

    pool_size, max_overflow = budget.process_pool(settings.database_process_role)
    connect_args: dict[str, int] = {}
    if settings.database_pool_mode == "pgbouncer_transaction":
        connect_args = {
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        }
    engine = create_async_engine(
        settings.database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=settings.database_pool_timeout_seconds,
        pool_recycle=settings.database_pool_recycle_seconds,
        pool_pre_ping=True,
        pool_use_lifo=True,
        connect_args=connect_args,
    )
    configure_pool_metrics(
        engine,
        process_role=settings.database_process_role,
        pool_capacity=pool_size + max_overflow,
        budget=budget,
    )
    return engine


def create_operator_engine(settings: Settings) -> AsyncEngine:
    """Create a separate, reserve-bounded engine for explicit operator commands."""
    budget = database_budget(settings)
    budget.validate()
    backend = make_url(settings.database_url).get_backend_name()
    connect_args: dict[str, int] = {}
    if settings.database_pool_mode == "pgbouncer_transaction":
        connect_args = {
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        }
    if backend != "postgresql":
        return create_async_engine(
            settings.database_url,
            poolclass=NullPool,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
    return create_async_engine(
        settings.database_url,
        pool_size=budget.operator_reserve,
        max_overflow=0,
        pool_timeout=settings.database_pool_timeout_seconds,
        pool_recycle=settings.database_pool_recycle_seconds,
        pool_pre_ping=True,
        pool_use_lifo=True,
        connect_args=connect_args,
    )


def create_session_factory(
    engine: AsyncEngine,
    settings: Settings,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        sync_session_class=TenantGuardedSession,
        expire_on_commit=False,
        autoflush=False,
        info={
            "database_application_role": settings.database_application_role,
            "statement_timeout_ms": settings.database_statement_timeout_ms,
            "idle_transaction_timeout_ms": (
                settings.database_idle_transaction_timeout_ms
            ),
        },
    )
