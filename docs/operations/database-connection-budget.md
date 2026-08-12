# Database connection budget and PgBouncer rollout

## Pilot envelope and formula

The repository baseline supports 1–3 pilot customers, 25 concurrent users, ten
concurrent calculations, independently scalable API and worker roles, three API
replicas, three worker replicas and a 40% connection safety margin. Queueing is
intentional: user and calculation concurrency must not be translated one-for-one
into PostgreSQL sessions.

Use the managed PostgreSQL connection limit after subtracting any connections that
the provider withholds from the customer-visible limit. The application validates:

```text
api replicas × (api pool size + API overflow)
+ worker replicas × (worker pool size + worker overflow)
+ migration connections
+ monitoring connections
+ operator reserve
+ floor(managed connection limit × safety margin percent / 100)
<= managed connection limit
```

The conservative repository example is `3 × (3 + 1) + 3 × (2 + 1) + 1 + 2 + 5
+ floor(50 × 40 / 100) = 49 <= 50`. The spare connection is rounding headroom, not
an allocatable pool. Staging and production refuse to start unless the hosting
environment explicitly supplies `DATABASE_CONNECTION_LIMIT`; all other values must
be reviewed against that limit whenever replicas or concurrency change.

`DATABASE_PROCESS_ROLE` selects only the local process pool (`api` or `worker`). It
does not allocate the aggregate budget inside one process. Migrations retain one
dedicated `NullPool` connection and execute only through the controlled single-run
job. Explicit manual platform-admin and governed factor-import commands use a
separate pool sized to `DATABASE_OPERATOR_RESERVE` with zero overflow, so they
cannot inherit API or worker capacity and excess concurrent commands fail after the
configured acquisition timeout. Monitoring and operator reserve are never
application overflow. Development SQLite operator connections remain disposable;
the controlled migration path retains its separate PostgreSQL `NullPool`.

## Direct PostgreSQL and PgBouncer

Use `DATABASE_POOL_MODE=direct` for a PostgreSQL endpoint. Use
`pgbouncer_transaction` only for an endpoint confirmed to use transaction pooling.
In transaction mode the application disables asyncpg's statement and prepared
statement caches, does not rely on session advisory state, and reapplies the
restricted database role, statement timeout, idle-transaction timeout and tenant
RLS context with transaction-local settings at every transaction start.

The source-controlled `config/pgbouncer/pgbouncer.ini.example` is a secure template,
not a deployable environment file. Render host, port, database and protected role
names from the secret/configuration system. Keep SCRAM authentication, transaction
mode, bounded client/server waits and `DISCARD ALL`; never commit a userlist or URL.
It binds only to loopback by default and requires certificate-verified TLS in both
directions. Keep the PgBouncer listener certificate/private key, client CA,
PostgreSQL client certificate/private key and PostgreSQL server CA in protected
secret mounts with least-privilege file permissions and a documented rotation
procedure. Certificates must contain names valid for the private endpoints used by
clients and PgBouncer. A remote PgBouncer service may replace loopback only with a
reviewed private-network listener, firewall policy that excludes public ingress and
equivalent egress controls. The controlled migration job must use the direct
PostgreSQL URL, never PgBouncer.

## Timeouts and telemetry

- connection acquisition: 5 seconds (`DATABASE_POOL_TIMEOUT_SECONDS`)
- ordinary statement: 30 seconds (`DATABASE_STATEMENT_TIMEOUT_MS`)
- ordinary idle transaction: 15 seconds
  (`DATABASE_IDLE_TRANSACTION_TIMEOUT_MS`)
- pool recycle: 15 minutes (`DATABASE_POOL_RECYCLE_SECONDS`)
- controlled migration statement: 10 minutes
- controlled migration idle transaction: 60 seconds
- controlled migration lock wait: 30 seconds by default

Prometheus records configured allocation, checked-out/capacity by process role,
acquisition duration and acquisition timeouts. Labels are limited to process role
and allocation; tenant identifiers, URLs and SQL parameters are forbidden. Alerts
fire at 80% sustained use, 250 ms p95 acquisition wait and any acquisition timeout.
`GET /api/v1/health/database-pool` exposes the same tenant-free local capacity as
`ok`, `saturated` or `exhausted` without acquiring another database connection.

## Inputs Henry must obtain for IONOS staging

Record these values in protected staging configuration and the capacity evidence,
not in Git:

1. managed PostgreSQL `max_connections` and the provider-reserved connection count;
2. whether the endpoint is direct PostgreSQL or PgBouncer, and its pooling mode;
3. protected direct migration endpoint and restricted application endpoint;
4. private endpoint names, allowed network paths, certificate identities, issuing
   CAs, protected certificate/key mount locations, ownership and rotation dates;
5. maximum and initial API and worker replica counts;
6. monitoring connection requirement and named operator reserve;
7. observed p95 connection acquisition, peak checked-out connections, PgBouncer
   wait queue and PostgreSQL active/idle counts during the approved capacity test;
8. maintenance window and escalation contact for connection-limit changes.

Do not record credentials, customer identifiers or hosting-specific addresses in
source control or shared test evidence.

## Staged rollout

1. Obtain the IONOS inputs and calculate the complete budget. Fail the change if the
   formula exceeds the usable limit.
2. Restore a sanitized staging database and run migrations through the existing
   controlled one-shot job on the direct endpoint.
3. Start one API replica in direct mode. Exercise authentication, tenant-isolated
   reads/writes, governed calculations and audit/report lineage.
4. Increase to the approved API replica count, then start workers one at a time.
   Confirm connection counts, acquisition p95 and pool saturation after each step.
5. If PgBouncer is approved, change one role at a time to transaction mode. Run the
   pooled tenant-isolation, reuse and exhaustion tests before progressing.
6. Run the 25-user/ten-calculation capacity scenario, retain exact-head evidence and
   recalculate the budget before any 3× growth change.

## Rollback and diagnosis

Rollback is configuration-only: restore the last reviewed replica, pool, overflow
and pooling-mode values, then restart one process role at a time. Do not run a
database downgrade, widen application role privileges, disable RLS, share migration
credentials or borrow from fixed reserves. Follow
`runbooks/database-connection-saturation.md` for alerts. A changed formula, managed
limit or replica count requires a new capacity review and adversarial tenant test.
