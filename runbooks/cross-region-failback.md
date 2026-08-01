# Cross-Region Failback

Failback is a planned migration, not a reverse failover.

1. Rebuild the preferred region from a base backup of the current primary.
2. Replay the current timeline's WAL until lag is below the accepted threshold.
3. Validate the rebuilt region as a read-only standby.
4. Freeze application writes and drain background jobs.
5. Confirm the current primary is healthy and the rebuilt target is caught up.
6. Fence the current primary or make it read-only.
7. Run `failback.sh` with explicit confirmation and the reviewed routing hook.
8. Promote the rebuilt target and switch global routing.
9. Restart application services in the preferred region.
10. Rebuild the former primary as a new standby.
11. Verify base backup, WAL archive, alerts, and restore readiness.

Never reuse the old primary data directory after timeline divergence.
