# Workload control and observability foundation

Status: implemented behind existing disabled worker feature flags. This tranche does not enable pilot traffic.

## Control boundary

The workload API exposes only tenant-scoped metadata and governed results. Raw payloads and protected diagnostics are never returned.

| Operation | Permitted roles |
|---|---|
| List, read and view queue snapshot | tenant_admin, sustainability_manager, data_reviewer |
| Enqueue a methodology dual-run | tenant_admin, sustainability_manager |
| Cancel a non-terminal workload | tenant_admin, sustainability_manager |

Platform administrators retain their existing controlled override through the shared authorization dependency.

## Factor lineage

A methodology dual-run accepts an emission-factor identifier rather than a caller-provided factor value. At enqueue time the service requires an active factor from an approved factor set and stores an immutable snapshot of:

- emission factor ID;
- factor-set ID and dataset version;
- source SHA-256;
- reporting year; and
- exact factor value.

The worker revalidates that snapshot before execution. Superseding a factor set does not invalidate already queued historical evidence, but altering or deleting its referenced source data causes the job to fail governed validation.

## Concurrency controls

Worker state transitions lock and reload the database row before checking the lease owner, executable status and lease expiry. Expired-lease recovery and claims use row locks with skip-locked semantics. Per-tenant active-workload limits prevent one tenant from consuming all worker capacity.

## Monitoring

Prometheus metrics expose workload type and state only; tenant identifiers are deliberately excluded from labels:

- `dcarbn_workload_queue_depth`;
- `dcarbn_workload_oldest_queued_age_seconds`;
- `dcarbn_workload_transitions_total`; and
- `dcarbn_workload_duration_seconds`.

The authenticated `/api/v1/workloads/metrics` endpoint provides each tenant with its own queue snapshot.

The governed rule set is stored in `deploy/monitoring/workload-alerts.yml`. Initial thresholds are:

| Condition | Threshold | Severity |
|---|---:|---|
| Oldest queued age | >60 seconds for 10 minutes | warning |
| Oldest queued age | >300 seconds for five minutes | critical |
| Dead-letter transition | any in 15 minutes | critical |
| Terminal failure ratio | >5% with at least 20 completions | warning |
| Queued work without success | 10 minutes | critical |

Operational response and rollback instructions are in `docs/operations/workload-pilot-runbook.md`.

## Capacity validation

The `Workload capacity validation` GitHub Actions workflow runs against a disposable PostgreSQL service. Its guarded harness creates isolated test tenants, enqueues representative durable workloads, runs concurrent worker loops, verifies tenant concurrency limits and records throughput and latency as a retained JSON artifact.

The default pull-request profile is deliberately small and repeatable: four tenants, 25 jobs per tenant, eight workers and a per-tenant active limit of four. A manual run can supply the agreed pilot shape. Results establish an initial capacity envelope only; production sizing still requires representative infrastructure and traffic.

## Fail-closed rollout scope

Workload submission and leasing are independently guarded. Setting a global flag is not sufficient.

- `ASYNC_WORKLOADS_ENABLED` must be true before the dual-run submission route accepts work or a worker leases work.
- `METHODOLOGY_PACKS_ENABLED` must also be true for the approved calculation pilot.
- `ASYNC_WORKLOAD_ALLOWED_TENANT_IDS` is a protected comma-separated allow-list of pilot tenant UUIDs.
- `ASYNC_WORKLOAD_ALLOWED_TYPES` is a comma-separated allow-list. The only currently reviewed value is `calculation`.
- Enabling asynchronous workloads with an empty tenant/type allow-list or without methodology packs causes configuration validation to fail.
- Read, status, queue metrics and cancellation remain available after rollback so authorised operators can inspect and safely close retained work.

The worker applies the same tenant/type scope in its database lease query. A disallowed tenant's queued work is neither selected nor made visible through another tenant's API.

## Pilot activation gate

Before enabling a worker feature flag:

1. CI and supply-chain security must pass.
2. Alert rules must be installed in the selected monitoring platform and routed to a named operator.
3. A representative capacity workflow run must pass and its JSON artifact must be retained.
4. An operator must verify retry, cancellation, dead-letter and rollback steps in the runbook.
5. Pilot approval must identify the tenant, allowed workload types, start time and rollback owner.

Passing this gate does not itself change `ASYNC_WORKLOADS_ENABLED` or `METHODOLOGY_PACKS_ENABLED`; both remain disabled until an explicit activation change is reviewed.


## Workload history pagination

`GET /api/v1/workloads` returns at most 100 records and uses the shared opaque
`(created_at, id)` cursor contract. Status and workload-type filters remain
tenant-scoped and align with composite database indexes. A modified cursor or a
cursor issued for another tenant is rejected with HTTP 422; an empty page is not
used to conceal an invalid token.
