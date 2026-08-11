# Controlled workload pilot activation plan

Status: preparation only. This plan does not enable workload processing or methodology-pack execution.

## Purpose

Run one evidence-only methodology dual-run pilot for one approved tenant while preserving the synchronous calculation path as the sole customer-facing authority. The pilot must prove operational control, tenant isolation, calculation equivalence and safe rollback before any broader rollout.

## Fixed pilot scope

| Item | Approved initial boundary |
|---|---|
| Workload type | `calculation` only |
| Operation | `methodology_dual_run` only |
| Governed method | Scope 1 stationary diesel litres |
| Customer result authority | Existing synchronous calculation path |
| Asynchronous output | Comparison evidence only |
| Tenant count | One explicitly approved pilot tenant |
| Methodology packs | One approved, effective-dated pack |
| Emission factors | One active factor from an approved factor set |
| Production writes | No replacement or mutation of customer calculation results |

Data import, report export, connector synchronisation and additional calculation methods remain outside this pilot.

## Mandatory engineering gate

Do not enable either feature flag until the application enforces the rollout scope in code.

The implementation must:

1. reject new asynchronous submissions when `ASYNC_WORKLOADS_ENABLED=false`;
2. reject methodology dual-run submissions when `METHODOLOGY_PACKS_ENABLED=false`;
3. allow submissions only for an explicit tenant-ID allow-list;
4. allow workers to lease only explicitly permitted workload types and tenants;
5. fail closed when an allow-list is empty, malformed or unavailable;
6. retain the existing tenant and role authorization checks;
7. record activation, rejection and rollback decisions without exposing tenant identifiers in Prometheus labels; and
8. include adversarial tests proving that a non-pilot tenant cannot enqueue, view, cancel or have work leased from the pilot queue.

This gate is required because environment flags alone do not express the documented one-tenant, one-workload pilot boundary.

## Named approvals

Complete this record before activation.

| Responsibility | Name | Approval/evidence |
|---|---|---|
| Business owner | To be assigned | |
| Pilot tenant | To be selected | Tenant UUID retained in protected deployment configuration |
| Pilot customer contact | To be assigned | |
| Technical pilot owner | To be assigned | |
| On-call operator | To be assigned | |
| Rollback owner | To be assigned | |
| Security approver | To be assigned | |
| Start time and duration | To be agreed | |
| Change/approval reference | To be created | |

Do not place tenant UUIDs, credentials, access tokens or personal contact details in this repository.

## Readiness checklist

### Code and evidence

- [ ] The tenant/workload rollout enforcement described above is merged.
- [ ] CI passes on the exact release commit.
- [ ] Supply-chain security passes on the exact release commit.
- [ ] The representative PostgreSQL capacity workflow passes.
- [ ] Its JSON artifact is retained with the pilot approval.
- [ ] The approved methodology pack passes schema and golden-example validation.
- [ ] Stationary-diesel dual-run equivalence passes with representative fictional data.
- [ ] Cross-tenant enqueue, read, cancellation and leasing tests pass.
- [ ] Feature flags still default to false in source and deployment templates.

### Infrastructure and operations

- [ ] Henry's hosting environment is available, but hosting access remains separated from application approval.
- [ ] Database backup and point-in-time recovery evidence is current.
- [ ] Database connection budgets and worker concurrency are documented.
- [ ] Prometheus workload rules are installed.
- [ ] Alerts route to the named operator and have been test-fired.
- [ ] Queue, retry, cancellation, dead-letter and lease-recovery procedures have been rehearsed.
- [ ] Protected logs and tenant-scoped workload diagnostics are accessible to authorised operators.
- [ ] The rollback owner can change the relevant flags without a new application deployment.

### Business and data

- [ ] The pilot tenant has accepted the limited evidence-only purpose.
- [ ] The approved reporting year, factor set and methodology-pack version are recorded.
- [ ] No real credentials or unnecessary personal data are present in pilot inputs.
- [ ] The synchronous calculation remains available throughout the pilot.
- [ ] Success, stop and acceptance criteria are signed off.

## Staged activation sequence

### Stage 0 — deploy dark

Deploy the validated application with:

```text
ASYNC_WORKLOADS_ENABLED=false
METHODOLOGY_PACKS_ENABLED=false
```

Apply migrations through the controlled migration job. Confirm health, database connectivity, metrics, alerts and rollback access. No asynchronous work may be accepted or leased.

### Stage 1 — scope configuration

Install the protected pilot tenant allow-list and permit only the `calculation` workload type. Confirm a non-pilot tenant is rejected and no existing queued item falls outside the approved scope.

Flags remain false.

### Stage 2 — methodology readiness

Load or select the approved stationary-diesel methodology pack and approved emission factor. Record pack ID/version, factor-set ID/version, source hash and reporting year in the protected approval record.

Flags remain false.

### Stage 3 — enable evidence-only pilot

Enable only the settings required for the approved dual-run path during the agreed window. Submit a small fictional or approved representative batch. The synchronous result remains authoritative; the worker output is comparison evidence only.

### Stage 4 — observe

Monitor:

- queue depth and oldest queued age;
- successful, failed and dead-letter transitions;
- p50, p95 and p99 latency;
- lease expiry and retry activity;
- database connections and saturation;
- per-tenant active-workload limit; and
- exact comparison equivalence and lineage completeness.

### Stage 5 — close or roll back

At the end of the window, disable the flags unless a separate continuation approval exists. Retain workloads, comparison results, alerts, capacity evidence and the approval decision.

## Immediate stop conditions

Disable the affected workload path immediately if any of the following occurs:

- cross-tenant visibility, submission, cancellation or leasing;
- a missing or mismatched factor or methodology lineage field;
- a non-zero governed comparison delta that is not explained and approved;
- any dead-lettered pilot workload;
- repeated lease expiry or duplicate execution;
- critical queue-age or stalled-processing alert;
- database saturation, connection-budget breach or customer-facing degradation;
- unexpected mutation of a synchronous calculation result; or
- loss of monitoring, audit evidence or rollback access.

## Rollback procedure

1. Set both pilot feature flags to false.
2. Stop new asynchronous submissions.
3. Allow verified healthy in-flight work to finish or cancel it through the governed API.
4. Preserve queued and terminal records; do not edit payloads or evidence in place.
5. Confirm the synchronous path remains healthy.
6. Record the trigger, affected scope, evidence, decision owner and corrective action.
7. Require a new approval before reactivation.

## Success criteria

The pilot succeeds only when:

- all approved workloads reach the expected terminal state;
- no non-pilot tenant can interact with the pilot path;
- no workload is dead-lettered;
- tenant concurrency remains within the configured limit;
- every comparison is exactly equivalent or has an approved documented explanation;
- methodology and factor lineage are complete and immutable;
- no customer-facing reliability regression is observed;
- alerts and rollback have been demonstrated; and
- the business, technical and security owners approve the evidence.

Success authorises assessment of a later rollout proposal. It does not automatically authorise additional tenants, workload types, methodology packs or production-result authority.

## Next implementation tranche

Implement the mandatory tenant/workload rollout gate behind disabled defaults, add adversarial tests, and submit it as a separate reviewed pull request. After that PR passes validation, populate the named approvals and run the plan against the staging environment.
