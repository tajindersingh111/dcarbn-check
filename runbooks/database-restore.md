# PostgreSQL Database Restore

## Preconditions

- Incident commander authorization.
- Confirmed target environment and database URL.
- Selected encrypted backup and matching manifest.
- Age identity available through the secret manager.
- Application write traffic stopped.
- Existing database snapshot retained where feasible.

## Procedure

1. Verify manifest SHA-256 against the encrypted backup.
2. Restore first into an isolated drill database.
3. Validate `alembic_version`, tenant counts, inventory counts, calculation runs,
   audit reports, and representative report hashes.
4. Provision or clean the production recovery database.
5. Run `restore.sh` with `RESTORE_CONFIRMATION=RESTORE-D-CARBN`.
6. Apply any migrations newer than the restored backup.
7. Rotate database credentials when compromise is possible.
8. Start one backend instance and run smoke tests.
9. Re-enable traffic gradually while monitoring errors, latency, and security events.
10. Create a new verified backup immediately after recovery.

Logical backups provide recovery to the latest completed backup. Point-in-time
recovery requires PostgreSQL WAL archiving or a managed database PITR feature.
