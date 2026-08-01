# GitOps Drift

1. Confirm the Argo CD application revision, sync state, health, and orphaned resources.
2. Compare live resources with the rendered Kustomize overlay.
3. Preserve live manifests before remediation when unexpected manual changes may contain evidence.
4. Revert unauthorized live changes through Git; do not normalize manual production edits.
5. Pause automated sync only when drift remediation could worsen an active incident.
6. Restore automated self-healing after the desired state is reviewed and merged.
7. Collect reconciliation evidence and confirm the application returns to `Synced` and `Healthy`.
