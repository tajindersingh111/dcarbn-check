# PostgreSQL Unavailable

1. Stop write traffic when database consistency is uncertain.
2. Check container or managed-service health, disk space, connections, and logs.
3. Confirm whether the primary is reachable and whether failover is available.
4. Never initialize an empty replacement over the existing data volume.
5. For corruption or data loss, invoke `database-restore.md`.
6. After recovery, run migrations, tenant-count checks, calculation-result checks,
   and audit-report hash sampling.
7. Re-enable writes only after application smoke tests and backup health pass.
