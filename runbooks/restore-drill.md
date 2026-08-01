# Restore Drill

Run at least monthly and after backup-system changes.

```bash
docker compose \
  --env-file .env.production \
  -f docker-compose.production.yml \
  --profile restore-drill \
  run --rm restore-drill
```

Record backup ID, restore duration, validation results, observed RPO, observed
RTO, operator, and any corrective action. A list-only integrity check is not a
restore drill.
