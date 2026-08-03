#!/usr/bin/env bash
set -Eeuo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
env_file="${ENV_FILE:-$root_dir/deploy/ionos/staging.env}"

if [[ ! -f "$env_file" ]]; then
  echo "Missing environment file: $env_file" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
. "$env_file"
set +a

: "${STAGING_DOMAIN:?STAGING_DOMAIN is required}"

for attempt in $(seq 1 40); do
  if curl --fail --silent --show-error \
      "https://$STAGING_DOMAIN/api/v1/health/live" >/dev/null &&
    curl --fail --silent --show-error \
      "https://$STAGING_DOMAIN/" >/dev/null; then
    echo "Staging health verification passed."
    exit 0
  fi
  sleep 3
done

echo "Staging health verification failed." >&2
exit 1
