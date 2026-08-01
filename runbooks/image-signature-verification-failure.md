# Image Signature or Provenance Verification Failure

1. Do not deploy the image.
2. Confirm the image is referenced by immutable digest.
3. Verify the expected GitHub workflow identity and OIDC issuer.
4. Inspect Cosign signature, transparency-log entry, SBOM attestation, and SLSA provenance.
5. Confirm the provenance subject digest matches the registry digest.
6. Rebuild on a trusted runner when identity, digest, or provenance is inconsistent.
7. Escalate as a supply-chain incident when tampering or credential compromise is possible.
