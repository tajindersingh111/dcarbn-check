# Automated Regional Failover Exercise

1. Confirm archive, PITR, standby role, and replay-lag health.
2. Run `dry-run` weekly and `simulation` monthly.
3. Reserve destructive promotion exercises for an approved maintenance window.
4. Capture pre- and post-exercise health responses, RPO, RTO, smoke-test results, and operator notes.
5. Sign the evidence bundle with the dedicated Ed25519 evidence key.
6. Upload signed evidence to immutable release evidence storage.
7. Block releases when the latest passing exercise is older than policy.
8. Rebuild the standby after any destructive promotion.
