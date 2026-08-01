# Continuous WAL Archiving, PITR and Cross-Region Failover

## Architecture

The primary PostgreSQL service runs with:

```text
wal_level=replica
archive_mode=on
archive_timeout=60s
max_wal_senders=10
max_replication_slots=10
hot_standby=on
```

`archive_command` encrypts each completed WAL segment with age, writes a
SHA-256 manifest, retains a local cache, and copies the archive to primary and
secondary rclone remotes. PostgreSQL retries failed archive commands and retains
the source WAL until the command succeeds.

Physical base backups use `pg_basebackup` in plain format with streamed WAL.
The resulting data directory is tarred, encrypted, checksummed, copied to both
regions, and retained independently from logical audit backups.

## Recovery targets

The PITR preparer accepts one recovery target:

```text
PITR_TARGET_TIME
PITR_TARGET_LSN
PITR_TARGET_XID
PITR_TARGET_NAME
```

No target means recovery to the latest available WAL. `PITR_TARGET_TIMELINE`
defaults to `latest`. Target action defaults to `pause` for operator inspection.

## Cross-region standby

The standby region is bootstrapped from the latest physical base backup and
uses `standby.signal` plus `restore_command` to continuously consume encrypted
WAL from the secondary archive. This is an archive-fed warm standby. Its RPO is
bounded by WAL switching, archive upload, and replay delay.

For lower RPO, add synchronous or asynchronous PostgreSQL streaming replication
over a private cross-region network while retaining archive recovery as the
fallback. Streaming replication is intentionally not enabled by the supplied
public Compose configuration because secure inter-region networking and
certificate identity are deployment-specific.

## Promotion

Promotion is controlled by `failover.sh`. It requires:

- Explicit confirmation.
- An exclusive operation lock.
- Primary health evaluation.
- A provider-specific fencing hook.
- Standby recovery state.
- Replay lag below the configured threshold.
- Successful `pg_promote`.
- Optional authoritative routing hook.

The sample hooks only print actions and must be replaced before production.

## Recovery objectives

With `archive_timeout=60s`, healthy object replication, and no intentional
replay delay, the design targets an archive-based RPO of approximately several
minutes. This is not guaranteed until measured through regional failure and
restore exercises.

RTO depends on declaration, fencing, promotion, regional application startup,
routing convergence, and validation. Measure it through scheduled failover
exercises.

## Region bootstrap

```bash
STANDBY_PREPARE_CONFIRMATION=PREPARE-STANDBY-D-CARBN \
docker compose \
  --env-file .env.standby \
  -f docker-compose.region-standby.yml \
  --profile standby-bootstrap \
  run --rm standby-prepare

docker compose \
  --env-file .env.standby \
  -f docker-compose.region-standby.yml \
  up -d standby-postgres standby-redis failover-status
```

## Security

- Base backups and WAL are encrypted before remote upload.
- The age private identity is available only in recovery environments.
- Regional remotes should use versioning, immutability, and separate credentials.
- Fencing and routing hooks should use short-lived workload identities.
- Database, archive, and failover secrets must be region-scoped.
- Recovery and failover actions must be recorded in the incident log.
