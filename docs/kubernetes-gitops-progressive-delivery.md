# Kubernetes, GitOps and Progressive Delivery

## Deployment model

The repository uses Kustomize for environment composition, Argo CD for
reconciliation, Argo Rollouts for canary delivery, External Secrets for runtime
secret synchronization, and Kyverno or Gatekeeper for policy enforcement.

Environment overlays:

```text
deploy/kubernetes/overlays/staging
deploy/kubernetes/overlays/production-primary
deploy/kubernetes/overlays/production-standby
```

Production images are digest-pinned. Promotion updates only the overlay image
digests and records a JSON evidence bundle.

## Required cluster services

Install and configure these before synchronizing the application:

```text
Ingress controller
Certificate manager
External Secrets Operator
Argo CD
Argo Rollouts
Kyverno or Gatekeeper
Metrics server
Prometheus-compatible monitoring
RWX evidence storage class
```

The supplied manifests do not install these controllers because production
installation, identity, storage, and lifecycle choices are cluster-specific.

## GitOps workflow

1. CI builds, scans, signs, and attests images.
2. Release gates verify supply-chain, resilience, SLO, backup, WAL, and PITR evidence.
3. The promotion script writes immutable backend and frontend digests to the selected overlay.
4. A reviewed Git change is merged.
5. Argo CD detects the desired-state change and reconciles the cluster.
6. Argo Rollouts shifts traffic through canary stages.
7. Prometheus analysis decides whether progression continues or aborts.
8. Reconciliation and rollout evidence is retained for operations and audit.

## Canary policy

Backend traffic progresses through:

```text
5% → analysis → 25% → analysis → 50% → analysis → 100%
```

Analysis checks API success rate, p95 latency, and PITR readiness. Frontend
progression checks availability before full promotion. Failed analysis stops the
rollout and preserves the stable service.

## Standby region

The standby overlay deploys with zero application replicas and ingress returning
503. Regional database promotion and fencing occur first. The standby promotion
script then changes the overlay replica counts through Git, after which Argo CD
starts the regional application stack.

## Policy enforcement

Kyverno policies enforce:

```text
Digest-pinned signed images
SBOM and provenance attestations
Non-root execution
RuntimeDefault seccomp
Read-only root filesystems
Dropped capabilities
Resource requests and limits
Readiness and liveness probes
Required labels
No hostPath volumes
Explicit storage classes
Default-deny networking
```

Gatekeeper examples provide an alternative for required labels, probes, and
approved registries. Run one authoritative enforcement strategy to avoid
duplicated or conflicting policy ownership.

## Secrets

ExternalSecret resources reference environment-specific ClusterSecretStores.
No live secret material belongs in Git. Secret stores should use workload
identity and separate primary, standby, and staging access policies.

## Validation

```bash
kustomize build deploy/kubernetes/overlays/staging
kustomize build deploy/kubernetes/overlays/production-primary
kustomize build deploy/kubernetes/overlays/production-standby
```

The GitOps workflow renders overlays, validates schemas, checks immutable image
references, evaluates Kyverno policies, compiles promotion scripts, and retains
manifest checksums.
