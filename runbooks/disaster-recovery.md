# Disaster Recovery

## Objectives

Set contractual values during operational acceptance. The supplied defaults
target:

- Logical-backup RPO: 24 hours.
- Initial service RTO target: 4 hours.
- Monthly restore drill.
- 35-day local retention plus separately governed remote retention.

These are deployment targets, not guarantees.

## Recovery order

1. Establish incident command and select the recovery region or environment.
2. Provision networking, secret management, PostgreSQL, Redis, and object storage.
3. Restore PostgreSQL from the latest verified encrypted backup.
4. Start Redis; restore AOF when valid or accept counter/session-cache loss.
5. Apply migrations and validate tenant, inventory, result, and report integrity.
6. Deploy backend, frontend, gateway, and observability using immutable images.
7. Rotate credentials and signing keys when the original environment may be compromised.
8. Run smoke, security, and audit-report hash checks.
9. Update DNS or load-balancer routing gradually.
10. Create a new backup and record observed RPO/RTO.

For an RPO below the backup interval, use managed PostgreSQL PITR or implement
continuous WAL archiving to separate immutable storage.
