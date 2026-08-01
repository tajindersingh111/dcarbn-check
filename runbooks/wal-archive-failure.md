# WAL Archive Failure

1. Check `dcarbn_wal_archive_age_seconds` and PostgreSQL `pg_stat_archiver`.
2. Inspect the failing WAL segment, archive command exit status, disk space,
   age recipient, rclone configuration, and both regional object stores.
3. Confirm the local encrypted WAL cache has capacity.
4. Do not delete unshipped WAL segments from `pg_wal`.
5. Restore remote connectivity or credentials and force a WAL switch:

```sql
SELECT pg_switch_wal();
```

6. Confirm `last_archived_wal` advances and both regional copies exist.
7. Run a PITR restore drill covering the affected interval.
8. Escalate immediately when WAL accumulation threatens primary disk capacity.
