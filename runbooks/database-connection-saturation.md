# Database connection saturation

## Signals

- `DCarbnDatabasePoolSaturated`: a process role has held at least 80% of its
  configured SQLAlchemy capacity for ten minutes.
- `DCarbnDatabasePoolWaitHigh`: p95 acquisition and transaction initialization
  exceeds 250 ms for ten minutes.
- `DCarbnDatabasePoolExhausted`: at least one acquisition exceeded
  `DATABASE_POOL_TIMEOUT_SECONDS` in five minutes.

Metrics expose only `process_role`; tenant identifiers and connection strings must
not be added to labels, alerts or shared incident evidence.

## Diagnose

1. Confirm whether `api` or `worker` is saturated and compare checked-out
   connections with its configured capacity.
2. Inspect slow statements, blocked statements, idle transactions and PostgreSQL
   connection counts by database role. Do not record statement parameters or tenant
   identifiers in shared evidence.
3. Confirm that API and worker replica counts match the values used by the budget
   formula and that no ordinary process is running Alembic.
4. For PgBouncer, confirm transaction mode, wait queues, server connection counts,
   authentication failures and that the application has cache disabling enabled.
5. Check whether the managed connection limit or reserved provider connections
   changed since the last capacity review.

## Stabilize

- Stop unapproved replica growth and pause nonessential durable worker claims.
- Prefer reducing concurrency or correcting a slow/blocked transaction before
  increasing a pool.
- Never take connections from the operator reserve, monitoring allocation, migration
  job or safety margin to silence an alert.
- If a database failover or outage is in progress, follow the PostgreSQL availability
  and failover runbooks instead.

## Roll back

Restore the last reviewed pool sizes, overflows, replica counts and direct/PgBouncer
mode as one configuration change. Restart one process role at a time, verify tenant
isolation and wait metrics, then continue. Do not bypass controlled migration locks
or disable row-level security during recovery.
