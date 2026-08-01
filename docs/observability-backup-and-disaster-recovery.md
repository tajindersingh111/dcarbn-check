# Observability, Backup and Disaster Recovery

## Backup model

PostgreSQL logical backups run inside the `backup` service. Each backup:

1. Uses PostgreSQL custom format with maximum compression.
2. Verifies the archive with `pg_restore --list`.
3. Encrypts the archive with age.
4. Writes a SHA-256 manifest.
5. Optionally copies the encrypted archive and manifest to object storage
   through rclone.
6. Applies local retention only after a successful backup.
7. Publishes backup freshness to the backend operational-health endpoint.

Default targets:

```text
Backup interval: 24 hours
Local retention: 35 days
Maximum healthy backup age: 26 hours
Restore-drill interval: 30 days
Logical-backup RPO target: 24 hours
Initial RTO target: 4 hours
```

These values are operational targets and require acceptance testing.

## Restore verification

A valid restore test must decrypt and restore the backup into an isolated
PostgreSQL instance. Listing archive contents alone is only an integrity
check.

Manual drill:

```bash
docker compose \
  --env-file .env.production \
  -f docker-compose.production.yml \
  --profile restore-drill \
  run --rm restore-drill
```

Optional scheduled drill:

```bash
docker compose \
  --env-file .env.production \
  -f docker-compose.production.yml \
  --profile automated-restore-drill \
  up -d restore-postgres restore-drill-scheduler
```

## Point-in-time recovery

The included logical-backup system restores to the latest completed dump.
Recovery between dumps requires continuous PostgreSQL WAL archiving or a
managed database point-in-time recovery feature. WAL archives must be
encrypted, immutable, stored separately from the primary, and tested.

## Observability stack

The observability overlay includes:

- Prometheus for metrics and alert evaluation.
- Alertmanager and the internal alert relay for email or webhook delivery.
- Grafana for dashboards.
- Loki and Promtail for structured logs.
- Tempo for distributed traces.
- OpenTelemetry Collector for trace and metric transport.
- PostgreSQL, Redis, host, and container exporters.

Start the platform and observability overlay together:

```bash
docker compose \
  --env-file .env.production \
  -f docker-compose.production.yml \
  -f docker-compose.observability.yml \
  up --build -d
```

Access Grafana through an authenticated private ingress or an SSH tunnel.
Do not expose Prometheus, Alertmanager, Loki, Tempo, or exporters publicly.

## Application telemetry

The backend exports:

```text
dcarbn_http_requests_total
dcarbn_http_request_duration_seconds
dcarbn_http_requests_in_progress
dcarbn_security_events_total
dcarbn_dependency_health
dcarbn_backup_age_seconds
dcarbn_backup_last_success
```

`/api/v1/health/operational` reports PostgreSQL, Redis, and backup state.
`/metrics` is intended for internal Prometheus scraping.

## Alert ownership

Every alert annotation references a runbook under `runbooks/`. Replace
relative runbook URLs with the deployed operations-documentation URL when
integrating Alertmanager with incident-management tooling.

## Log and trace correlation

Structured application logs include correlation IDs and, when tracing is
active, OpenTelemetry trace and span IDs. Grafana links Loki logs to Tempo
traces through the trace ID field.

## Recovery evidence

Preserve for every drill or incident:

- Backup ID and manifest checksum.
- Backup and restore timestamps.
- Observed RPO and RTO.
- Migration version.
- Tenant, inventory, calculation, and audit-report validation counts.
- Representative audit-report hashes.
- Operator, reviewer, outcome, and remediation actions.
