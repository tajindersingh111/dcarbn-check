# API Unavailable

1. Confirm the alert with `/api/v1/health/live` and `/api/v1/health/ready`.
2. Check gateway, backend, PostgreSQL, and Redis container health and recent logs.
3. Inspect deployment changes, restart counts, memory pressure, and disk space.
4. If only one backend instance is unhealthy, remove it from service and replace it.
5. If PostgreSQL or Redis is unavailable, follow the corresponding dependency runbook.
6. Roll back the latest release when failure began immediately after deployment.
7. Validate login, dashboard loading, activity creation, and audit-report retrieval.
8. Record downtime, affected tenants, root cause, and corrective actions.
