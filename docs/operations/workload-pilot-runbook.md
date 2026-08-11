# Workload pilot operations runbook

Status: pre-pilot. Worker feature flags remain disabled until every activation gate has recorded approval.

## Ownership and safety boundary

The pilot owner, on-call operator and rollback owner must be named before activation. Alerts aggregate only by workload type; tenant identifiers must never be added to Prometheus labels. Investigations that require tenant context use the authenticated tenant-scoped workload API and audit trail.

The capacity workflow is permitted only against its disposable CI database. It refuses to run unless both `APP_ENV=test` and `ALLOW_DESTRUCTIVE_CAPACITY_TEST=1` are set.

## Queue age

Warning: oldest queued age exceeds 60 seconds for 10 minutes. Critical: it exceeds 300 seconds for five minutes.

1. Confirm the affected workload type and whether successful transitions continue.
2. Check worker health, database connections, lease expiry and queue depth.
3. Pause new pilot submissions if age continues to rise.
4. Do not raise concurrency until database saturation and tenant fairness have been checked.
5. Roll back the applicable worker feature flag if the critical condition persists for 10 minutes.

## Dead-letter growth

Any dead-letter transition is critical during the pilot.

1. Keep the work item immutable and retain its correlation identifiers.
2. Inspect the protected diagnostic record and audit trail; do not copy secrets into tickets.
3. Classify the cause as input, methodology, provider, infrastructure or software.
4. Correct the underlying cause before retrying or replaying.
5. If two items share the same software or infrastructure cause, disable the affected workload type.

## Failure rate

A warning fires when failed plus dead-lettered terminal transitions exceed 5% over 15 minutes with at least 20 completions.

1. Separate expected governed rejections from software and infrastructure errors.
2. Compare the affected versioned methodology pack and factor lineage.
3. Stop the affected workload type if the ratio remains above 5% for a second window.
4. Record the decision, evidence and recovery owner.

## Stalled processing

A critical alert fires when queued work exists but no success is recorded for 10 minutes.

1. Confirm workers are running and can obtain database leases.
2. Check for exhausted connection budgets, long transactions and expired leases.
3. Verify that a single tenant is not consuming the configured active-workload limit.
4. Disable the affected workload type if processing cannot be restored within 10 minutes.

## Retry, cancellation and lease recovery

- Retry only retryable failures after their root cause is understood.
- Cancellation is allowed only for a non-terminal workload and must record the acting user.
- Expired leases return to queued state until the maximum attempt count is reached.
- A workload that exhausts attempts becomes dead-lettered and requires operator review.
- Never edit workload payloads or result evidence in place.

## Capacity evidence

The `Workload capacity validation` workflow records:

- tenant and workload counts;
- enqueue and processing throughput;
- p50, p95 and p99 end-to-end latency;
- observed maximum active work per tenant;
- terminal-state totals; and
- the pass/fail thresholds used for that run.

The JSON artifact is an initial CI capacity envelope, not a production sizing guarantee. Before pilot activation, run the workflow with the agreed pilot shape and retain the artifact with the approval record.

## Activation and rollback

Activation must identify the pilot tenant, allowed workload types, start time and rollback owner. Enable only the explicitly approved worker feature flag. Do not enable methodology-pack activation merely because worker validation passes.

Rollback order:

1. Disable the affected worker feature flag.
2. Stop new submissions for the affected workload type.
3. Allow healthy in-flight work to complete or cancel it through the governed API.
4. Preserve queued and terminal records for investigation.
5. Record the incident, decision and follow-up action.
