# Software Supply-Chain Security

## Controls

The build pipeline performs source secret scanning, Python and Node dependency
audits, deterministic container builds, SPDX and CycloneDX SBOM generation,
Grype and Trivy vulnerability scanning, license-policy evaluation, keyless
Cosign image signing, SBOM attestation, SLSA provenance generation, and
post-build verification.

Production images must be referenced by digest. The release gate requires a
passing supply-chain assurance bundle before approval.

## Vulnerability policy

High and Critical findings with an available fix block release. Exceptions are
stored in `deploy/supply-chain/vulnerability-exceptions.yml` and must include an
owner, reason, approval, and future expiry. Expired or incomplete exceptions are
ignored.

## Signing identity

CI uses GitHub Actions OIDC keyless signing. Verification constrains the
certificate identity to the repository supply-chain workflow and the GitHub
token-actions issuer. Production clusters should enforce the same identity with
Kyverno or an equivalent admission controller.

## SBOMs

Each image produces:

```text
SPDX JSON
CycloneDX JSON
SHA-256 checksums
SBOM generation evidence
```

SBOMs and scan evidence are retained for 365 days by the supplied workflow.
Registry attestations remain attached to immutable image digests.

## Provenance

The workflow publishes build provenance for the image digest through GitHub
artifact attestations and the registry. Provenance should identify the source
repository, commit, workflow, builder, and immutable subject digest.

## Release requirements

A production release requires:

```text
Digest-pinned image references
Valid keyless Cosign signatures
SPDX SBOM attestations
SLSA provenance
Passing vulnerability policy
Passing license policy
Passing secret scan
Passing dependency audits
Passing resilience and SLO release gates
```

Admission policies are examples and must be tested against the deployed Kyverno
or Gatekeeper version before enforcement.
