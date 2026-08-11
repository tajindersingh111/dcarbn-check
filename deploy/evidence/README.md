# Deployment evidence directory

This directory is the host-side exchange for controlled database migration evidence.
Do not commit generated JSON records.

Before a contract or other high-risk migration, operators must place fresh records at:

- `backup-status.json` with `verified: true` and `latest_success_at`;
- `pitr-status.json` with `verified: true` and `latest_base_backup_at`.

The controlled migration job writes `migration.json` atomically. The staging workflow
retrieves that redacted record as release evidence after a successful deployment.
