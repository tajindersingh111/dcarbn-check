# Software Supply-Chain Compromise

1. Freeze deployments and preserve registry, CI, signing, provenance, and audit logs.
2. Identify affected commits, workflows, dependencies, images, digests, signatures, and environments.
3. Revoke compromised tokens, workload identities, signing keys, and registry credentials.
4. Block affected image digests through the admission controller and registry policy.
5. Rebuild from a reviewed commit on a clean runner with fresh credentials.
6. Generate new SBOMs, vulnerability results, provenance, signatures, and release evidence.
7. Compare runtime artifacts against trusted digests and replace affected workloads.
8. Notify security, operations, tenants, and regulators according to the incident policy.
