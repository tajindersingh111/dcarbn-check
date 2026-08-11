# Platform capacity envelope and load-test runbook

Status: implementation baseline. No live capacity claim is approved until the signed staging evidence passes review.

## Pilot assumptions

The first measurement profile models four pilot tenants, 25 concurrent interactive users, up to 50,000 activity rows per inventory, 100 accounting synchronisation records per tenant and two pre-generated audit reports per test tenant. The existing worker harness separately measures four tenants, 25 queued jobs per tenant and eight worker loops.

These are planning assumptions, not contractual limits. Increase them only after a successful baseline run and database, Redis, worker and API telemetry review.

## Initial candidate envelope

- API p95 latency: at most 1 second.
- API p99 latency: at most 2 seconds.
- Request error rate: at most 1% during the test window.
- Timeout rate: at most 0.5%.
- Tenant p95 ratio: no slower tenant may exceed 1.5 times the fastest tenant under the same profile.
- Minimum evidence volume: 1,000 requests over a five-minute run.
- Operating margin: normal pilot traffic must remain at or below 60% of the highest passing concurrency until two repeatable staging runs agree within 15%.

The stricter existing 30-day availability and server-error SLOs remain authoritative. These short-run thresholds are diagnostic release gates, not a relaxation of service objectives.

## Safety boundary

The runner refuses to start unless all of the following are true:

1. The profile declares `local`, `staging` or `pilot`, never production.
2. The exact target hostname appears in the reviewed profile.
3. A protected approval reference is supplied.
4. The exact non-production confirmation phrase is supplied.
5. Write scenarios are disabled unless a separate disposable-data confirmation is supplied.

Never use production credentials, customer records or an unapproved public endpoint. Use fictional tenant data and short-lived test identities. Output contains tenant aliases only; tokens, tenant identifiers, inventory identifiers and report identifiers are not written to evidence.

## Test phases

1. **Contract** — run unit, compile and profile validation in every relevant pull request.
2. **Interactive baseline** — authentication, dashboard, bounded activity lists, accounting synchronisation history, workload history and report downloads across two tenant aliases.
3. **Controlled heavy work** — use a separately reviewed profile with disposable data for large imports, concurrent calculations and report generation. Mutations remain off in the committed example.
4. **Worker recovery** — run the existing workload capacity workflow, then exercise retry, lease recovery and Redis/database interruption in the isolated staging window.
5. **Soak** — after baseline approval, run the passing concurrency for at least 60 minutes and compare resource and latency drift.

## Protected staging configuration

Create the GitHub environment `performance-staging` with required reviewers. Configure its base URL and approval reference as environment variables, and its two short-lived tenant tokens as secrets. Set the fictional inventory and report IDs as environment variables. Do not place their real values in Git, tickets or public logs.

The manual `Platform capacity envelope` workflow binds the reviewed profile to that protected host, runs the test, produces a SHA-256 checksum and keyless-signs the JSON evidence with GitHub OIDC.

## Telemetry to retain

Retain the runner evidence alongside screenshots or exports for:

- API and worker CPU and memory;
- database connections, pool wait, locks and slow queries;
- Redis latency and queue depth;
- worker queue age, execution duration and retry count;
- dataset sizes and the exact release SHA; and
- interruption start, recovery time and any dropped or duplicated work.

The runner records throughput, p50, p95, p99, errors, timeouts, scenario totals and tenant-alias fairness. Infrastructure telemetry is collected from the existing Prometheus/Grafana stack because the runner must not receive database or observability administrator credentials.

## Decision and evidence record

The application owner, security reviewer, operations owner and business pilot owner review the signed artifact. Record GO only when thresholds pass, tenant isolation remains intact, no resource is saturated above 70%, and a 40% operating margin remains. Every failure receives an owner, remediation decision and retest reference.

The signed record must contain the immutable release SHA, approval reference, protected environment, profile, timestamps, measurements, assertions and result. It must not contain credentials, customer data or stable tenant identifiers.

## Current known baseline

The merged workload-only validation completed 100 of 100 jobs across four isolated tenants with no dead letters, maximum observed active work of three against a limit of four, enqueue throughput of 248.73 jobs/second, processing throughput of 52.27 jobs/second and p95 end-to-end latency of 1.836 seconds. This supports the queue design only; it does not yet establish end-to-end platform capacity.

## Completion gate for issue #53

Issue #53 remains open until an approved staging run supplies the signed evidence, infrastructure telemetry, cross-tenant isolation result, bottleneck owners and the final safe pilot concurrency. Hosting availability is therefore a measurement dependency, not a reason to weaken or bypass the guardrail.

