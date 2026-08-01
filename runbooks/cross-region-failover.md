# Cross-Region Failover

## Safety rules

- Promotion requires fencing the old primary first.
- A healthy primary is not failed over without explicit override.
- Only one failover controller may hold the operation lock.
- DNS or traffic-manager routing changes occur after successful promotion.
- Redis is recreated in the target region; PostgreSQL remains the source of truth.
- Never run both regions as writable primaries.

## Procedure

1. Declare the regional incident and assign an incident commander.
2. Confirm base-backup and WAL replication health in the standby region.
3. Confirm the standby is in recovery and replay lag is below the accepted limit.
4. Execute the provider-specific fencing hook for the old primary.
5. Run the failover controller:

```bash
FAILOVER_CONFIRMATION=FAILOVER-D-CARBN \
docker compose \
  --env-file .env.standby \
  -f docker-compose.region-standby.yml \
  --profile regional-failover \
  run --rm failover-controller
```

6. Confirm `pg_is_in_recovery()` is false in the promoted region.
7. Start the regional application profile:

```bash
docker compose \
  --env-file .env.standby \
  -f docker-compose.region-standby.yml \
  --profile regional-app \
  up --build -d
```

8. Run authentication, inventory, activity, DATa, approval, locking, and
   audit-report smoke tests.
9. Confirm global routing points only to the promoted region.
10. Create a new base backup and verify WAL archiving on the new timeline.
11. Preserve the old region for evidence until it is rebuilt as a standby.

## Abort conditions

Abort before promotion when fencing fails, replay lag exceeds the limit, WAL
archives are missing, the standby is not in recovery, or the target database
fails integrity checks.
