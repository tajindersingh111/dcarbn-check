#!/usr/bin/env bash
set -Eeuo pipefail

[[ "${FAILOVER_CONFIRMATION:-}" == "FAILOVER-D-CARBN" ]] || {
  echo "Set FAILOVER_CONFIRMATION=FAILOVER-D-CARBN to proceed." >&2
  exit 1
}

region="${FAILOVER_TARGET_REGION:?FAILOVER_TARGET_REGION is required}"
state_file="${FAILOVER_STATE_FILE:-/failover-state/failover.json}"
lock_file="${FAILOVER_LOCK_FILE:-/failover-state/failover.lock}"
primary_health_url="${PRIMARY_HEALTH_URL:?PRIMARY_HEALTH_URL is required}"
if [[ -n "${STANDBY_DATABASE_URL_FILE:-}" && -f "${STANDBY_DATABASE_URL_FILE}" ]]; then
  standby_database_url="$(cat "${STANDBY_DATABASE_URL_FILE}")"
else
  standby_database_url="${STANDBY_DATABASE_URL:?STANDBY_DATABASE_URL is required}"
fi
routing_hook="${ROUTING_FAILOVER_HOOK:-}"
fencing_hook="${PRIMARY_FENCING_HOOK:-}"

mkdir -p "$(dirname "$state_file")"
exec 9>"$lock_file"
flock -n 9 || {
  echo "Another failover operation is active." >&2
  exit 1
}

if curl --fail --silent --max-time 5 "$primary_health_url" >/dev/null; then
  [[ "${ALLOW_HEALTHY_PRIMARY_FAILOVER:-false}" == "true" ]] || {
    echo "Primary is healthy. Refusing failover without explicit override." >&2
    exit 1
  }
fi

[[ -n "$fencing_hook" ]] || {
  echo "PRIMARY_FENCING_HOOK is required to prevent split brain." >&2
  exit 1
}

"$fencing_hook"

deadline=$((SECONDS + ${FAILOVER_REPLAY_TIMEOUT_SECONDS:-300}))
while (( SECONDS < deadline )); do
  in_recovery="$(psql "$standby_database_url" -Atc \
    "SELECT pg_is_in_recovery();")"
  replay_lag="$(psql "$standby_database_url" -Atc \
    "SELECT COALESCE(EXTRACT(EPOCH FROM now() - pg_last_xact_replay_timestamp()), 0);")"

  if [[ "$in_recovery" == "t" ]] &&
     awk "BEGIN {exit !($replay_lag <= ${FAILOVER_MAX_REPLAY_LAG_SECONDS:-30})}"; then
    break
  fi
  sleep 5
done

psql "$standby_database_url" \
  --set=ON_ERROR_STOP=1 \
  --command="SELECT pg_promote(true, 60);"

promoted="$(psql "$standby_database_url" -Atc \
  "SELECT NOT pg_is_in_recovery();")"
[[ "$promoted" == "t" ]] || {
  echo "Standby promotion failed." >&2
  exit 1
}

if [[ -n "$routing_hook" ]]; then
  "$routing_hook" "$region"
fi

timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
jq -n \
  --arg region "$region" \
  --arg promoted_at "$timestamp" \
  '{
    status: "promoted",
    active_region: $region,
    promoted_at: $promoted_at,
    primary_fenced: true
  }' > "${state_file}.tmp"
chmod 0644 "${state_file}.tmp"
mv "${state_file}.tmp" "$state_file"

echo "Failover to ${region} completed."
