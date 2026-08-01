# Split-Brain Prevention

Split brain occurs when more than one PostgreSQL region accepts writes.

Controls:

- Provider-level fencing before promotion.
- Failover operation locking.
- Health and replay-lag gates.
- A single authoritative global-routing system.
- Separate database credentials for active and standby application stacks.
- Application profile disabled in the standby region until promotion.
- Timeline and role state monitoring.
- No automatic promotion solely from a failed health check.

When split brain is suspected:

1. Stop application writes in both regions.
2. Fence both database endpoints from application traffic.
3. Record timelines, LSNs, transaction timestamps, and audit evidence.
4. Select one authoritative history under incident-command approval.
5. Rebuild the losing region from the authoritative primary.
6. Reconcile externally visible actions before reopening traffic.
