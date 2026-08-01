#!/usr/bin/env bash
set -Eeuo pipefail

image="${1:?Digest-pinned image reference is required}"
policy_file="${SUPPLY_CHAIN_POLICY_FILE:-/config/policy.yml}"
output_dir="${2:-/artifacts/verification}"
artifact_name="$(basename "$image" | tr ':@/' '---')"

[[ "$image" == *@sha256:* ]] || {
  echo "Image reference must be pinned by digest." >&2
  exit 1
}

mkdir -p "$output_dir"

identity="$(yq -r '.signing.certificate_identity_regexp' "$policy_file")"
issuer="$(yq -r '.signing.certificate_oidc_issuer' "$policy_file")"

cosign verify \
  --certificate-identity-regexp "$identity" \
  --certificate-oidc-issuer "$issuer" \
  "$image" \
  > "${output_dir}/${artifact_name}.signature.json"

cosign verify-attestation \
  --type spdxjson \
  --certificate-identity-regexp "$identity" \
  --certificate-oidc-issuer "$issuer" \
  "$image" \
  > "${output_dir}/${artifact_name}.sbom-attestation.json"

cosign verify-attestation \
  --type slsaprovenance \
  --certificate-identity-regexp "$identity" \
  --certificate-oidc-issuer "$issuer" \
  "$image" \
  > "${output_dir}/${artifact_name}.provenance-attestation.json"

jq -n \
  --arg image "$image" \
  --arg verified_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{
    schema_version: 1,
    evidence_type: "image_verification",
    image: $image,
    verified_at: $verified_at,
    signature: true,
    sbom_attestation: true,
    provenance_attestation: true,
    result: "passed"
  }' > "${output_dir}/${artifact_name}.verification-evidence.json"
