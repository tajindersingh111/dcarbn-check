#!/usr/bin/env bash
set -Eeuo pipefail

source_path="${1:?Source path or image reference is required}"
output_dir="${2:-/artifacts/sbom}"
artifact_name="${SBOM_ARTIFACT_NAME:-$(basename "$source_path" | tr ':/' '--')}"

mkdir -p "$output_dir"

syft "$source_path" \
  --output "spdx-json=${output_dir}/${artifact_name}.spdx.json" \
  --output "cyclonedx-json=${output_dir}/${artifact_name}.cyclonedx.json"

sha256sum \
  "${output_dir}/${artifact_name}.spdx.json" \
  "${output_dir}/${artifact_name}.cyclonedx.json" \
  > "${output_dir}/${artifact_name}.sbom.sha256"

jq -n \
  --arg artifact "$source_path" \
  --arg generated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg spdx "${artifact_name}.spdx.json" \
  --arg cyclonedx "${artifact_name}.cyclonedx.json" \
  '{
    schema_version: 1,
    evidence_type: "sbom_generation",
    artifact: $artifact,
    generated_at: $generated_at,
    formats: {
      spdx_json: $spdx,
      cyclonedx_json: $cyclonedx
    },
    result: "passed"
  }' > "${output_dir}/${artifact_name}.sbom-evidence.json"
