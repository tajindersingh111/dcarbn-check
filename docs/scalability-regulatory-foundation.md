# Scalability and regulatory-change foundation

This tranche establishes two opt-in boundaries without removing the existing synchronous customer routes.

## Durable workloads

`durable_workloads` is the database delivery authority for calculations, data imports, report exports and connector synchronisations. Every work item is tenant scoped and has:

- a tenant-unique idempotency key;
- explicit queued, leased, running, succeeded, failed, cancelled and dead-lettered states;
- bounded attempts, scheduling, lease expiry and heartbeat fields;
- organisation/inventory scope;
- redacted payload, result and diagnostics;
- progress and failure metadata.

Workers claim rows using a database lock, enforce a per-tenant active-job limit, recover expired leases and dispatch only through a reviewed handler registry. Raw exception text is not persisted. The existing request-path implementations remain authoritative until workload-specific handlers, operational metrics and load-test evidence are complete.

### Rollout

1. Keep `ASYNC_WORKLOADS_ENABLED=false`.
2. Register one reviewed handler and dual-run it against representative fictional data.
3. Compare results and lineage with the synchronous path.
4. Enable one tenant and workload type.
5. Observe queue depth, oldest-job age, execution time, retry and failure rates.
6. Roll back by disabling enqueue; retained jobs remain auditable and may be cancelled.

## Methodology packs

`methodology_packs` adds immutable semantic versions selected by owner, pack key, jurisdiction, framework and reporting date. Packs contain only configuration and reference a small reviewed operator library. Arbitrary formulas, functions, imports, scripts and customer-authored code are rejected.

The lifecycle is draft, reviewed, approved, superseded or withdrawn. Preparation, review and approval identities must be separate. Approval requires schema validation, a registered operator and exact Decimal golden examples.

PostgreSQL triggers prevent overlapping approved effective periods, deletion of governed packs and content changes after approval. Withdrawal or supersession retains historical evidence.

### Calculation lineage

A pack-enabled calculation must snapshot:

- methodology-pack ID, key and semantic version;
- operator identifier;
- factor-set ID and version;
- inventory/reporting date and selection inputs;
- calculation software version.

A newer pack never alters an approved or locked historical result. Restatement is an explicit governed action.

## First controlled integration

The first registered calculation handler supports only `methodology_dual_run`. It compares the existing synchronous activity-factor engine with the approved `uk.scope1.stationary_diesel.litres` pack using identical activity, factor and allocation inputs.

The handler:

- accepts only the reviewed governed-method-to-pack mapping;
- loads an approved platform or tenant-owned pack;
- performs exact Decimal comparison;
- returns pack ID, version, operator, source reference and both results;
- never writes or replaces customer calculation results;
- treats invalid payloads as non-retryable and persists only a generic safe error.

`ASYNC_WORKLOADS_ENABLED` and `METHODOLOGY_PACKS_ENABLED` remain false. The integration is evidence-only until representative tenant dual runs, queue metrics and operational acceptance are complete.

## Next increments

- Add role-controlled enqueue/status/cancel APIs.
- Add Prometheus queue and worker metrics.
- Capture the approved factor-set ID/version in every dual-run request.
- Convert further governed methods only after stationary-diesel equivalence evidence is accepted.
- Register import, report-export and connector-sync handlers after workload-specific recovery tests.
- Run concurrency, termination-recovery, adversarial tenant and load tests.
