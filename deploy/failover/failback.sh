#!/usr/bin/env bash
set -Eeuo pipefail

[[ "${FAILBACK_CONFIRMATION:-}" == "FAILBACK-D-CARBN" ]] || {
  echo "Set FAILBACK_CONFIRMATION=FAILBACK-D-CARBN to proceed." >&2
  exit 1
}

current_primary_url="${CURRENT_PRIMARY_DATABASE_URL:?CURRENT_PRIMARY_DATABASE_URL is required}"
rebuilt_target_url="${REBUILT_TARGET_DATABASE_URL:?REBUILT_TARGET_DATABASE_URL is required}"
routing_hook="${ROUTING_FAILBACK_HOOK:-}"
target_region="${FAILBACK_TARGET_REGION:?FAILBACK_TARGET_REGION is required}"

target_recovery="$(psql "$rebuilt_target_url" -Atc "SELECT pg_is_in_recovery();")"
[[ "$target_recovery" == "t" ]] || {
  echo "Failback target must be a rebuilt standby." >&2
  exit 1
}

lag="$(psql "$rebuilt_target_url" -Atc \
  "SELECT COALESCE(EXTRACT(EPOCH FROM now() - pg_last_xact_replay_timestamp()), 0);")"
awk "BEGIN {exit !($lag <= ${FAILBACK_MAX_REPLAY_LAG_SECONDS:-10})}" || {
  echo "Failback target replay lag is too high: ${lag}s." >&2
  exit 1
}

[[ "${APPLICATION_WRITES_FROZEN:-false}" == "true" ]] || {
  echo "Freeze application writes before failback." >&2
  exit 1
}

psql "$rebuilt_target_url" \
  --set=ON_ERROR_STOP=1 \
  --command="SELECT pg_promote(true, 60);"

if [[ -n "$routing_hook" ]]; then
  "$routing_hook" "$target_region"
fi

echo "Failback to ${target_region} completed."
