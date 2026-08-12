from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from prometheus_client import Counter, Gauge, Histogram
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.pool import ConnectionPoolEntry, PoolProxiedConnection
from sqlalchemy.pool import QueuePool

from app.db.connection_budget import DatabaseConnectionBudget, DatabaseProcessRole

DATABASE_POOL_CONNECTIONS = Gauge(
    "dcarbn_database_pool_connections",
    "SQLAlchemy connections by process role and state.",
    ["process_role", "state"],
)
DATABASE_POOL_ACQUISITION = Histogram(
    "dcarbn_database_pool_acquisition_seconds",
    "Time to acquire and initialize a database connection.",
    ["process_role"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)
DATABASE_POOL_TIMEOUTS = Counter(
    "dcarbn_database_pool_timeouts_total",
    "Database pool acquisition timeouts.",
    ["process_role"],
)
DATABASE_CONNECTION_BUDGET = Gauge(
    "dcarbn_database_connection_budget",
    "Configured PostgreSQL connection budget by allocation.",
    ["allocation"],
)


@dataclass(frozen=True, slots=True)
class DatabasePoolHealth:
    status: str
    process_role: DatabaseProcessRole
    capacity: int
    checked_out: int
    utilisation_percent: float


def database_pool_health(
    engine: AsyncEngine,
    *,
    process_role: DatabaseProcessRole,
    configured_capacity: int,
) -> DatabasePoolHealth:
    pool = engine.sync_engine.pool
    if not isinstance(pool, QueuePool):
        return DatabasePoolHealth(
            status="not_applicable",
            process_role=process_role,
            capacity=0,
            checked_out=0,
            utilisation_percent=0.0,
        )

    checked_out = pool.checkedout()
    utilisation = checked_out / configured_capacity
    if checked_out >= configured_capacity:
        status = "exhausted"
    elif utilisation >= 0.8:
        status = "saturated"
    else:
        status = "ok"
    return DatabasePoolHealth(
        status=status,
        process_role=process_role,
        capacity=configured_capacity,
        checked_out=checked_out,
        utilisation_percent=round(utilisation * 100, 2),
    )


def configure_pool_metrics(
    engine: AsyncEngine,
    *,
    process_role: DatabaseProcessRole,
    pool_capacity: int,
    budget: DatabaseConnectionBudget,
) -> None:
    role = process_role
    DATABASE_POOL_CONNECTIONS.labels(process_role=role, state="capacity").set(
        pool_capacity
    )
    DATABASE_POOL_CONNECTIONS.labels(process_role=role, state="checked_out").set(0)
    for allocation, value in (
        ("limit", budget.connection_limit),
        ("safety_margin", budget.safety_margin),
        ("operator_reserve", budget.operator_reserve),
        ("monitoring", budget.monitoring_connections),
        ("migration", budget.migration_connections),
        ("api", budget.api_connections),
        ("worker", budget.worker_connections),
    ):
        DATABASE_CONNECTION_BUDGET.labels(allocation=allocation).set(value)

    def checkout(
        dbapi_connection: object,
        connection_record: ConnectionPoolEntry,
        connection_proxy: PoolProxiedConnection,
    ) -> None:
        DATABASE_POOL_CONNECTIONS.labels(
            process_role=role,
            state="checked_out",
        ).inc()

    def checkin(
        dbapi_connection: object,
        connection_record: ConnectionPoolEntry,
    ) -> None:
        DATABASE_POOL_CONNECTIONS.labels(
            process_role=role,
            state="checked_out",
        ).dec()

    event.listen(engine.sync_engine.pool, "checkout", checkout)
    event.listen(engine.sync_engine.pool, "checkin", checkin)


def acquisition_started() -> float:
    return perf_counter()


def observe_acquisition(process_role: DatabaseProcessRole, started: float) -> None:
    DATABASE_POOL_ACQUISITION.labels(process_role=process_role).observe(
        perf_counter() - started
    )


def record_acquisition_timeout(process_role: DatabaseProcessRole) -> None:
    DATABASE_POOL_TIMEOUTS.labels(process_role=process_role).inc()
