#!/usr/bin/env bash
set -Eeuo pipefail

target="${1:?Image or filesystem target is required}"
output_dir="${2:-/artifacts/scans}"
artifact_name="${SCAN_ARTIFACT_NAME:-$(basename "$target" | tr ':/' '--')}"
severity="${VULNERABILITY_SEVERITIES:-HIGH,CRITICAL}"

mkdir -p "$output_dir"

grype "$target" \
  --output json \
  > "${output_dir}/${artifact_name}.grype.json"

trivy image \
  --format json \
  --severity "$severity" \
  --ignore-unfixed=false \
  --output "${output_dir}/${artifact_name}.trivy.json" \
  "$target"

python /scripts/evaluate-vulnerability-policy.py \
  --grype "${output_dir}/${artifact_name}.grype.json" \
  --trivy "${output_dir}/${artifact_name}.trivy.json" \
  --policy "${SUPPLY_CHAIN_POLICY_FILE:-/config/policy.yml}" \
  --exceptions "${VULNERABILITY_EXCEPTIONS_FILE:-/config/vulnerability-exceptions.yml}" \
  --output "${output_dir}/${artifact_name}.vulnerability-policy.json"
