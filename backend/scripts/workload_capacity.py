from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections.abc import Sequence
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import (  # noqa: F401
    activity,
    audit,
    boundary,
    calculation,
    data_integration,
    data_review,
    emission_factor,
    factor_resolution,
    identity,
    inventory,
    inventory_governance,
    methodology,
    methodology_pack,
    organisation,
    security,
    tenant,
    workload,
)
from app.models.tenant import Tenant
from app.models.workload import DurableWorkload, WorkloadStatus, WorkloadType
from app.services.workloads import (
    enqueue_workload,
    lease_next_workload,
    mark_running,
    succeed_workload,
)


def percentile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(round((len(ordered) - 1) * fraction), len(ordered) - 1)
    return ordered[index]


async def count_completed(
    session_factory: async_sessionmaker[AsyncSession],
    tenant_ids: list[UUID],
) -> int:
    async with session_factory() as session:
        value = await session.scalar(
            select(func.count(DurableWorkload.id)).where(
                DurableWorkload.tenant_id.in_(tenant_ids),
                DurableWorkload.status == WorkloadStatus.SUCCEEDED,
            )
        )
    return int(value or 0)


async def monitor_active(
    session_factory: async_sessionmaker[AsyncSession],
    tenant_ids: list[UUID],
    stop: asyncio.Event,
    observed_maximums: dict[UUID, int],
) -> None:
    while not stop.is_set():
        async with session_factory() as session:
            rows = (
                await session.execute(
                    select(
                        DurableWorkload.tenant_id,
                        func.count(DurableWorkload.id),
                    )
                    .where(
                        DurableWorkload.tenant_id.in_(tenant_ids),
                        DurableWorkload.status.in_(
                            (WorkloadStatus.LEASED, WorkloadStatus.RUNNING)
                        ),
                    )
                    .group_by(DurableWorkload.tenant_id)
                )
            ).all()
        for tenant_id, active in rows:
            observed_maximums[tenant_id] = max(
                observed_maximums.get(tenant_id, 0),
                int(active),
            )
        await asyncio.sleep(0.005)


async def worker(
    *,
    worker_number: int,
    session_factory: async_sessionmaker[AsyncSession],
    tenant_ids: list[UUID],
    total_jobs: int,
    completed: asyncio.Event,
    simulated_work_seconds: float,
    lease_seconds: int,
    per_tenant_limit: int,
) -> None:
    worker_id = f"capacity-worker-{worker_number}"
    while not completed.is_set():
        async with session_factory() as session:
            workload = await lease_next_workload(
                session,
                worker_id=worker_id,
                lease_seconds=lease_seconds,
                per_tenant_limit=per_tenant_limit,
            )
            if workload is not None and workload.tenant_id in tenant_ids:
                running = await mark_running(session, workload, worker_id=worker_id)
                await asyncio.sleep(simulated_work_seconds)
                await succeed_workload(
                    session,
                    running,
                    worker_id=worker_id,
                    result={"capacity_validation": True},
                )
        if workload is None:
            if await count_completed(session_factory, tenant_ids) >= total_jobs:
                completed.set()
                return
            await asyncio.sleep(0.01)


async def execute(args: argparse.Namespace) -> dict[str, Any]:
    if os.getenv("APP_ENV") != "test" or os.getenv("ALLOW_DESTRUCTIVE_CAPACITY_TEST") != "1":
        raise RuntimeError(
            "Capacity validation is restricted to APP_ENV=test with "
            "ALLOW_DESTRUCTIVE_CAPACITY_TEST=1."
        )

    database_url = os.environ["DATABASE_URL"]
    engine = create_async_engine(database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    run_id = uuid4().hex
    tenant_ids: list[UUID] = []

    try:
        async with session_factory() as session:
            tenants = [
                Tenant(
                    name=f"Capacity tenant {run_id[:8]} {index}",
                    slug=f"capacity-{run_id}-{index}",
                )
                for index in range(args.tenants)
            ]
            session.add_all(tenants)
            await session.commit()
            for tenant in tenants:
                await session.refresh(tenant)
            tenant_ids = [tenant.id for tenant in tenants]

        enqueue_started = perf_counter()
        async with session_factory() as session:
            for job_number in range(args.jobs_per_tenant):
                for tenant_number, tenant_id in enumerate(tenant_ids):
                    _, created = await enqueue_workload(
                        session,
                        tenant_id=tenant_id,
                        workload_type=WorkloadType.DATA_IMPORT,
                        idempotency_key=(
                            f"capacity:{run_id}:{tenant_number}:{job_number}"
                        ),
                        requested_by="capacity-validation",
                        payload={"job_number": job_number},
                        max_attempts=2,
                    )
                    if not created:
                        raise RuntimeError("Capacity workload was not created.")
        enqueue_seconds = perf_counter() - enqueue_started

        total_jobs = args.tenants * args.jobs_per_tenant
        completed = asyncio.Event()
        observed_maximums = {tenant_id: 0 for tenant_id in tenant_ids}
        processing_started = perf_counter()
        monitor = asyncio.create_task(
            monitor_active(
                session_factory,
                tenant_ids,
                completed,
                observed_maximums,
            )
        )
        workers = [
            asyncio.create_task(
                worker(
                    worker_number=number,
                    session_factory=session_factory,
                    tenant_ids=tenant_ids,
                    total_jobs=total_jobs,
                    completed=completed,
                    simulated_work_seconds=args.simulated_work_ms / 1000,
                    lease_seconds=args.lease_seconds,
                    per_tenant_limit=args.per_tenant_limit,
                )
            )
            for number in range(args.workers)
        ]
        await asyncio.wait_for(
            asyncio.gather(*workers),
            timeout=args.timeout_seconds,
        )
        completed.set()
        await monitor
        processing_seconds = perf_counter() - processing_started

        async with session_factory() as session:
            rows = list(
                (
                    await session.scalars(
                        select(DurableWorkload).where(
                            DurableWorkload.tenant_id.in_(tenant_ids)
                        )
                    )
                ).all()
            )
            terminal_rows = (
                await session.execute(
                    select(
                        DurableWorkload.status,
                        func.count(DurableWorkload.id),
                    )
                    .where(DurableWorkload.tenant_id.in_(tenant_ids))
                    .group_by(DurableWorkload.status)
                )
            ).all()

        latencies = [
            (row.completed_at - row.created_at).total_seconds()
            for row in rows
            if row.completed_at is not None
        ]
        terminal_counts = {
            status.value: int(count) for status, count in terminal_rows
        }
        enqueue_rps = total_jobs / max(enqueue_seconds, 0.001)
        processing_rps = total_jobs / max(processing_seconds, 0.001)
        p95_seconds = percentile(latencies, 0.95)
        maximum_active = max(observed_maximums.values(), default=0)

        assertions = {
            "all_jobs_succeeded": terminal_counts.get("succeeded", 0) == total_jobs,
            "no_dead_letters": terminal_counts.get("dead_lettered", 0) == 0,
            "tenant_limit_respected": maximum_active <= args.per_tenant_limit,
            "tenant_concurrency_observed": maximum_active > 0,
            "enqueue_throughput_met": enqueue_rps >= args.min_enqueue_rps,
            "processing_throughput_met": processing_rps >= args.min_processing_rps,
            "p95_latency_met": p95_seconds <= args.max_p95_seconds,
        }
        result: dict[str, Any] = {
            "profile": {
                "tenants": args.tenants,
                "jobs_per_tenant": args.jobs_per_tenant,
                "workers": args.workers,
                "simulated_work_ms": args.simulated_work_ms,
                "lease_seconds": args.lease_seconds,
                "per_tenant_limit": args.per_tenant_limit,
            },
            "capacity_envelope": {
                "total_jobs": total_jobs,
                "enqueue_seconds": round(enqueue_seconds, 3),
                "enqueue_jobs_per_second": round(enqueue_rps, 2),
                "processing_seconds": round(processing_seconds, 3),
                "processing_jobs_per_second": round(processing_rps, 2),
                "latency_p50_seconds": round(percentile(latencies, 0.50), 3),
                "latency_p95_seconds": round(p95_seconds, 3),
                "latency_p99_seconds": round(percentile(latencies, 0.99), 3),
                "maximum_active_per_tenant": maximum_active,
            },
            "terminal_counts": terminal_counts,
            "assertions": assertions,
            "passed": all(assertions.values()),
        }
        return result
    finally:
        if tenant_ids:
            async with session_factory() as session:
                await session.execute(delete(Tenant).where(Tenant.id.in_(tenant_ids)))
                await session.commit()
        await engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure the initial durable-workload capacity envelope."
    )
    parser.add_argument("--tenants", type=int, default=4)
    parser.add_argument("--jobs-per-tenant", type=int, default=25)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--simulated-work-ms", type=int, default=25)
    parser.add_argument("--lease-seconds", type=int, default=30)
    parser.add_argument("--per-tenant-limit", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--min-enqueue-rps", type=float, default=5)
    parser.add_argument("--min-processing-rps", type=float, default=5)
    parser.add_argument("--max-p95-seconds", type=float, default=30)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/workload-capacity.json"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = asyncio.run(execute(args))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit("Workload capacity validation failed.")


if __name__ == "__main__":
    main()
