# Backup Failure or Stale Backup

1. Inspect the backup container logs and `/api/v1/health/operational`.
2. Check PostgreSQL connectivity, backup volume capacity, age recipient, and remote storage.
3. Verify the latest encrypted file and manifest checksum.
4. Run an immediate one-off backup with `BACKUP_RUN_ONCE=true`.
5. Run the restore-drill profile against the latest successful backup.
6. Escalate as critical when no verified backup exists within the stated RPO.
7. Do not delete older verified backups until a new backup and restore drill pass.
