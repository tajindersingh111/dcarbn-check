# Controlled database migrations

## Purpose

Application replicas never run Alembic. A dedicated one-shot deployment service owns
schema changes, holds a PostgreSQL advisory lock and produces redacted release evidence.
An unsuccessful migration blocks application rollout.

## Release phases

1. **Expand** — additive, backwards-compatible schema only. Current and previous
   application versions must both operate against the expanded schema.
2. **Backfill** — resumable data movement in bounded batches. Large backfills must not
   be embedded in schema-locking Alembic transactions.
3. **Contract** — removal or enforcement that can break an old binary. The job refuses
   to start until old replicas are stopped and fresh backup and PITR evidence exists.

Every exact target and phase is reviewed in
`backend/app/db/migration_releases.json`. Deployments may not use the moving `head`
alias. The application contains an exact compatible-revision set and fails startup on
an unreviewed schema.

## Staging execution

1. Record the immutable release SHA and migration target.
2. Verify the protected GitHub environment approval.
3. For contract releases, rehearse the maintenance window and retire old replicas.
4. Place fresh `backup-status.json` and `pitr-status.json` in `deploy/evidence/`.
5. Run `deploy/ionos/deploy.sh`. It starts data services, retires old backend replicas
   where required, runs the one-shot migration, verifies the exact target, starts the
   new application and executes health checks.
6. Retain `migration.json` with the release evidence. It records the release SHA,
   previous and current revisions, phase, timestamps, duration and outcome; it never
   records database URLs, tenant identifiers or credentials.

## Failure and recovery

- Advisory-lock contention fails without running Alembic. Investigate the existing
  migration job; do not bypass the lock.
- Timeout or Alembic failure leaves rollout blocked. Preserve evidence and logs, inspect
  database locks and choose a forward fix by default.
- Application image rollback does not reverse schema. It is safe only while the old
  binary supports the current schema.
- A destructive migration requires an independently reviewed restore decision. Restore
  only after confirming backup identity, PITR point, expected data loss and stakeholder
  approval.
- Never run `alembic downgrade` as an automatic deployment response.

## Production-sized rehearsal

Before production, restore a representative sanitized snapshot to an isolated database,
run the exact migration target through the controlled job and retain duration, peak lock
wait, affected table sizes and post-migration verification. The approved timeout and
maintenance window must exceed the observed envelope with a documented margin.
