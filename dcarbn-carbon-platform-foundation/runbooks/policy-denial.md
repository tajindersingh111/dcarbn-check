# Kubernetes Policy Denial

1. Read the admission-controller denial message and identify the exact policy rule.
2. Correct the workload manifest, image signature, provenance, labels, probes, resources, or security context.
3. Validate the rendered overlay locally and in CI.
4. Do not disable enforcement or add broad exclusions to unblock a release.
5. Record emergency exceptions with owner, scope, expiry, and compensating controls.
6. Remove temporary exceptions immediately after the corrected release is deployed.
