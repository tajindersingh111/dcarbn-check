# Release Rollback

1. Freeze further deployments and record the failing image digests.
2. Confirm whether the migration is backward compatible.
3. Deploy the previous immutable backend and frontend images.
4. Do not downgrade the database unless an approved down-migration and backup exist.
5. Validate authentication, inventory reads, activity writes, DATa review,
   approvals, locks, and audit-report generation.
6. Monitor error rate, latency, and data integrity before closing the incident.
