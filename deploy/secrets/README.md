# Production secrets

Create the following files before starting the production stack:

```text
secrets/secret_key
secrets/mfa_encryption_key
secrets/database_url
secrets/redis_url
secrets/smtp_password
secrets/postgres_password
```

Each file must contain only the secret value and a trailing newline. Restrict
permissions to the deployment account:

```bash
chmod 600 secrets/*
```

Example URL formats:

```text
postgresql+asyncpg://dcarbn:<password>@postgres:5432/dcarbn
redis://:<password>@redis:6379/0
```

Do not commit populated secret files. Production should use the orchestrator's
native secret manager or an external secret-management service where available.


## Backup and observability secrets

Additional files:

```text
secrets/backup_age_recipient
secrets/backup_age_identity
secrets/restore_database_url
secrets/restore_postgres_password
secrets/grafana_admin_password
secrets/postgres_exporter_url
secrets/redis_password
```

Generate an age key pair outside the deployment host where possible:

```bash
age-keygen -o secrets/backup_age_identity
age-keygen -y secrets/backup_age_identity > secrets/backup_age_recipient
```

`restore_database_url` must target only the isolated restore-drill database.
`postgres_exporter_url` should use a dedicated least-privilege monitoring role.

Remote backup storage is configured through rclone. Keep object versioning,
retention locks, and provider credentials in the deployment platform's secret
manager. The age private identity must not be stored beside remote backups.


## WAL, PITR and regional failover secrets

Add:

```text
secrets/replication_database_url
secrets/standby_postgres_password
secrets/standby_application_database_url
secrets/standby_redis_url
```

`replication_database_url` must use a dedicated PostgreSQL role with `LOGIN`
and `REPLICATION`, restricted to the backup network.

Example role creation:

```sql
CREATE ROLE dcarbn_backup
  WITH LOGIN REPLICATION
  PASSWORD '<generated-secret>';
```

`standby_application_database_url` must point to the standby PostgreSQL service
and should remain inaccessible to the regional application profile until the
database is promoted. Use different archive-store credentials in each region
and grant each region only the minimum read/write access required.

The provider-specific fencing and routing hooks should use workload identity or
short-lived credentials rather than static credentials in the repository.


## Release evidence signing keys

Add:

```text
secrets/evidence_private_key
secrets/evidence_public_key
```

Generate an Ed25519 key pair outside the deployment host:

```bash
openssl genpkey -algorithm ED25519 -out secrets/evidence_private_key
openssl pkey -in secrets/evidence_private_key -pubout   -out secrets/evidence_public_key
chmod 600 secrets/evidence_private_key
chmod 644 secrets/evidence_public_key
```

The private key belongs only in the evidence-signing job. Release-gate jobs use
the public key. Rotate keys through a documented overlap period and preserve
the public key needed to verify historical evidence.
