# Controlled workload pilot — staging rollout checklist

Status: preparation only. Completing this document does not enable asynchronous workloads or methodology packs.

This checklist turns the controlled pilot plan into a single evidence-backed GO/NO-GO procedure for one tenant and the `calculation` / `methodology_dual_run` path. The synchronous calculation remains authoritative throughout.

## 1. Change record

Complete this section in the protected change record, not with customer identifiers in the repository.

| Field | Required value |
|---|---|
| Release commit | Exact immutable commit deployed to staging |
| Environment | Staging |
| Change/approval reference | Assigned reference |
| Approved pilot tenant | One tenant; UUID stored only in protected configuration |
| Methodology pack | Approved pack ID and version |
| Factor set | Approved set ID, version, source hash and reporting year |
| Activation window | Start, duration and time zone |
| Observation window | Minimum agreed monitoring period |
| Rollback owner | Named operator with tested configuration access |
| Evidence location | Protected retained evidence location |

## 2. Responsibility boundary

| Responsibility | Owner | Required evidence |
|---|---|---|
| Hosting readiness only | Henry | Environment, network, TLS, DNS, backup and access handover |
| Application release owner | Assign before GO | Exact release commit and deployment evidence |
| Business/pilot approval | Assign before GO | Approved purpose, tenant and window |
| Security approval | Assign before GO | Security workflow and secret-handling review |
| On-call monitoring | Assign before GO | Alert route and acknowledgement test |
| Rollback decision and execution | Assign before GO | Successful rollback rehearsal |

Henry's initial scope is hosting readiness. Hosting availability does not authorise application deployment, tenant configuration, feature-flag activation or access to customer data. Those actions remain with the named application, security and rollback owners.

## 3. Protected staging configuration

Use `deploy/staging/workload-pilot.env.example` as the configuration shape.

- [ ] `APP_ENV=staging`.
- [ ] `ASYNC_WORKLOADS_ENABLED=false`.
- [ ] `METHODOLOGY_PACKS_ENABLED=false`.
- [ ] `ASYNC_WORKLOAD_ALLOWED_TENANT_IDS` contains exactly one approved UUID in protected configuration and is empty in source control.
- [ ] `ASYNC_WORKLOAD_ALLOWED_TYPES=calculation`.
- [ ] `WORKER_LEASE_SECONDS=60`.
- [ ] `WORKER_PER_TENANT_LIMIT=2`.
- [ ] `REDIS_REQUIRED=true`.
- [ ] Secure cookies, HSTS and fail-closed rate limiting are enabled.
- [ ] Database, Redis, encryption, signing, OAuth and provider credentials are supplied through protected secrets only.
- [ ] No credentials, tenant identifiers or personal contact details appear in Git, CI logs or deployment artifacts.

## 4. Hosting handover from Henry

- [ ] Staging endpoint, region and environment identifier recorded.
- [ ] TLS certificate and DNS resolution verified.
- [ ] Private database and Redis connectivity verified.
- [ ] Inbound, outbound, proxy and firewall rules documented.
- [ ] Secret-storage mechanism available with least-privilege access.
- [ ] Database backup and point-in-time recovery capability confirmed.
- [ ] Persistent storage, retention and encryption settings recorded.
- [ ] Application, worker and controlled migration-job runtime targets available.
- [ ] Monitoring/log export path available.
- [ ] Hosting administrator access is separate from application approval authority.

## 5. Exact-release validation

Record links or artifact identifiers beside every completed item.

- [ ] PR #60 fail-closed rollout enforcement is present in the release commit.
- [ ] CI passes on the exact release commit.
- [ ] Supply-chain security passes on the exact release commit.
- [ ] Workload capacity validation passes on the exact release commit.
- [ ] Capacity JSON artifact is retained with the change record.
- [ ] Database migration dry run and controlled migration job pass.
- [ ] Methodology-pack schema and golden-example validation pass.
- [ ] Stationary-diesel equivalence passes using fictional or explicitly approved representative data.
- [ ] Cross-tenant enqueue, read, cancellation, leasing and expired-lease recovery tests pass.
- [ ] Dependency, secret, container, SBOM, signature and provenance results are retained.
- [ ] Release image digest is pinned and recorded.

## 6. Deploy dark

- [ ] Deploy the exact validated image with both feature flags false.
- [ ] Run migrations once through the controlled migration job.
- [ ] Confirm application and worker health endpoints.
- [ ] Confirm database and Redis connection budgets.
- [ ] Confirm no workload can be submitted or leased.
- [ ] Confirm the existing synchronous calculation journey remains healthy.
- [ ] Confirm authorised workload status, metrics and cancellation access remains available.
- [ ] Confirm the rollback owner can change protected flags without rebuilding the image.

## 7. Observability and recovery gate

- [ ] Install `deploy/monitoring/workload-alerts.yml`.
- [ ] Dashboard shows queue depth, oldest age, transitions, duration, retries, lease expiry and database saturation.
- [ ] Alerts route to the named on-call operator.
- [ ] Warning and critical alerts have been test-fired and acknowledged.
- [ ] Queue retry, cancellation, dead-letter and expired-lease recovery procedures have been rehearsed.
- [ ] Database restore or point-in-time recovery evidence is current.
- [ ] Application rollback to the previous image has been rehearsed.
- [ ] Configuration rollback to both flags false has been rehearsed.

## 8. Scope and methodology gate

Keep both feature flags false while completing this section.

- [ ] Protected tenant allow-list contains only the approved pilot tenant.
- [ ] A different tenant is rejected from submission.
- [ ] Worker leasing and expired-lease recovery ignore non-approved tenants and workload types.
- [ ] Approved methodology pack is immutable, effective-dated and within its validity window.
- [ ] Factor set is active, approved and appropriate for the reporting year.
- [ ] Pack, factor and source hashes are recorded in the protected change record.
- [ ] The pilot input contains no unnecessary personal data or live credentials.

## 9. GO/NO-GO decision

Every approver must record GO before activation.

| Decision | Owner | GO/NO-GO | Timestamp | Evidence/reference |
|---|---|---|---|---|
| Hosting ready | Henry | | | |
| Application ready | Application release owner | | | |
| Business scope approved | Business owner | | | |
| Security controls approved | Security approver | | | |
| Monitoring ready | On-call operator | | | |
| Rollback ready | Rollback owner | | | |

Any blank or NO-GO entry means both flags remain false.

## 10. Controlled activation

Apply one reviewed protected-configuration change during the approved window:

```text
METHODOLOGY_PACKS_ENABLED=true
ASYNC_WORKLOADS_ENABLED=true
```

Do not change the approved tenant or workload-type allow-lists in the same window.

- [ ] Record the configuration change identifier and timestamp.
- [ ] Confirm application startup validation succeeds.
- [ ] Submit one fictional or approved representative dual-run.
- [ ] Confirm the approved tenant can view only its own workload.
- [ ] Confirm a non-approved tenant receives a governed rejection.
- [ ] Confirm the worker leases only `calculation` work for the approved tenant.
- [ ] Confirm the synchronous result remains authoritative.
- [ ] Confirm comparison result and lineage are complete and immutable.

## 11. Observation window

Record measurements at the agreed interval.

- [ ] Queue depth and oldest queued age remain within thresholds.
- [ ] No dead-letter transitions occur.
- [ ] No unexpected retry, duplicate execution or lease-expiry pattern occurs.
- [ ] p50, p95 and p99 duration remain within the retained capacity envelope.
- [ ] Per-tenant concurrency does not exceed two.
- [ ] Database and Redis connections remain within budget.
- [ ] No customer-facing latency or reliability regression occurs.
- [ ] Governed comparison delta is zero or has a separately approved explanation.
- [ ] Audit, factor and methodology lineage remain complete.

## 12. Immediate stop conditions

Set both flags to false immediately for any:

- cross-tenant submission, visibility, cancellation, leasing or recovery;
- unexplained governed comparison delta;
- missing or mismatched methodology/factor lineage;
- dead-lettered pilot workload;
- repeated retry, duplicate execution or lease expiry;
- queue-age, stalled-processing or infrastructure-saturation critical alert;
- synchronous-path degradation or result mutation;
- loss of monitoring, audit evidence, secret control or rollback access.

## 13. Rollback checklist

- [ ] Set `ASYNC_WORKLOADS_ENABLED=false`.
- [ ] Set `METHODOLOGY_PACKS_ENABLED=false`.
- [ ] Restart or refresh application and workers through the controlled procedure.
- [ ] Confirm new submissions receive the disabled response.
- [ ] Confirm no worker leases new work.
- [ ] Finish verified healthy in-flight work or cancel it through the governed API.
- [ ] Preserve queued and terminal records; do not edit evidence in place.
- [ ] Confirm synchronous calculations remain healthy.
- [ ] Retain alerts, metrics, logs and the triggering evidence.
- [ ] Record decision owner, cause, impact and corrective action.
- [ ] Require a new GO decision before reactivation.

## 14. Closeout

- [ ] Both flags are returned to false at the end of the window unless a separate continuation approval exists.
- [ ] All approved workloads reached the expected terminal state.
- [ ] No non-pilot tenant interacted with the pilot path.
- [ ] Validation, capacity, monitoring and rollback evidence is retained.
- [ ] Business, application and security owners record acceptance or corrective actions.
- [ ] Any proposal to expand tenants, workload types or customer-result authority is handled as a new reviewed change.
