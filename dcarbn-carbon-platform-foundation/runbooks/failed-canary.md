# Failed Canary Rollout

1. Identify the failed analysis metric and the affected revision.
2. Confirm Argo Rollouts automatically stopped progression.
3. Run `deploy/progressive-delivery/abort-rollout.sh` when automated rollback has not completed.
4. Compare canary and stable logs, traces, error rates, latency, and dependency health.
5. Keep the stable revision serving traffic while the defect is investigated.
6. Fix the release through Git and create a new immutable image digest.
7. Do not retry the same digest without a documented false-positive analysis result.
