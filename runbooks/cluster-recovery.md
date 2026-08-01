# Kubernetes Cluster Recovery

1. Restore cluster control-plane availability or provision a replacement cluster.
2. Install required platform controllers: ingress, cert management, External Secrets,
   Argo CD, Argo Rollouts, Kyverno, observability, and storage drivers.
3. Register the replacement cluster with Argo CD using least-privilege credentials.
4. Apply the D-carbN AppProject, policy bundles, and environment Application.
5. Verify external secrets, managed PostgreSQL, Redis, evidence storage, DNS, and TLS.
6. Allow Argo CD to reconcile the desired state.
7. Confirm policy reports are clean and all rollouts are healthy.
8. Run recovery-readiness and release-gate checks before reopening traffic.
