# GitOps Emergency Rollback

1. Freeze promotions and identify the last known-good Git revision and image digests.
2. Verify database migration compatibility before application rollback.
3. Revert the production overlay in Git rather than patching live workloads.
4. Allow Argo CD to reconcile the reverted desired state.
5. Abort active canaries and verify stable services point to the restored revision.
6. Run authentication, inventory, activity, DATa, approval, lock, and reporting smoke tests.
7. Collect GitOps reconciliation and rollout evidence before resolving the incident.
