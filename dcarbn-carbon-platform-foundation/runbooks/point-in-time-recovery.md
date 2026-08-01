# Point-in-Time Recovery

## Preconditions

- Incident commander approval.
- Confirmed recovery target: timestamp, LSN, transaction ID, restore point, or latest.
- Selected recovery environment and empty PostgreSQL data volume.
- Base-backup and WAL archive access from at least one region.
- Age identity available through the secret manager.
- Application write traffic stopped for an in-place recovery.
- Existing primary fenced or isolated when recovery may replace it.

## Procedure

1. Confirm the intended recovery target and timezone in the incident log.
2. Select the newest verified base backup created before the target.
3. Verify the encrypted base-backup SHA-256 manifest.
4. Prepare the recovery data volume:

```bash
PITR_CONFIRMATION=RECOVER-D-CARBN \
PITR_TARGET_TIME="2026-08-01 10:42:00+00" \
docker compose \
  --env-file .env.production \
  -f docker-compose.production.yml \
  --profile pitr \
  run --rm pitr-restore
```

5. Start PostgreSQL against the prepared recovery volume in an isolated network.
6. Monitor PostgreSQL logs for requested WAL segments and recovery completion.
7. When `recovery_target_action=pause`, inspect the target before promotion.
8. Validate migration version, tenants, inventories, calculations, approvals,
   audit-report hashes, and the incident-specific corrected state.
9. Promote only after approval:

```sql
SELECT pg_wal_replay_resume();
SELECT pg_promote(true, 60);
```

10. Rotate credentials when compromise or unauthorized access caused recovery.
11. Start one backend instance, run smoke tests, then restore traffic gradually.
12. Create a new base backup immediately after promotion.

## Failure handling

- Missing WAL: verify both regional remotes and timeline history files.
- Target not reached: select an older base backup or correct the target timezone.
- Recovery passed the target: stop immediately and rebuild from a clean volume.
- Divergent timelines: never copy WAL between unrelated promoted timelines
  without a reviewed recovery plan.
