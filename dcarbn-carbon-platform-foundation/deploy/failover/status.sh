#!/usr/bin/env bash
set -Eeuo pipefail

if [[ -n "${DATABASE_URL_FILE:-}" && -f "${DATABASE_URL_FILE}" ]]; then
  database_url="$(cat "${DATABASE_URL_FILE}")"
else
  database_url="${DATABASE_URL:?DATABASE_URL is required}"
fi
region="${DCARBN_REGION:?DCARBN_REGION is required}"
state_file="${FAILOVER_STATE_FILE:-/failover-state/failover.json}"

in_recovery="$(psql "$database_url" -Atc "SELECT pg_is_in_recovery();")"
current_lsn="$(psql "$database_url" -Atc \
  "SELECT CASE WHEN pg_is_in_recovery() THEN pg_last_wal_replay_lsn() ELSE pg_current_wal_lsn() END;")"
replay_timestamp="$(psql "$database_url" -Atc \
  "SELECT COALESCE(pg_last_xact_replay_timestamp()::text, now()::text);")"
timeline="$(psql "$database_url" -Atc \
  "SELECT timeline_id FROM pg_control_checkpoint();")"

mkdir -p "$(dirname "$state_file")"
jq -n \
  --arg region "$region" \
  --argjson in_recovery "$([[ "$in_recovery" == "t" ]] && echo true || echo false)" \
  --arg current_lsn "$current_lsn" \
  --arg replay_timestamp "$replay_timestamp" \
  --arg timeline "$timeline" \
  --arg checked_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{
    region: $region,
    in_recovery: $in_recovery,
    current_lsn: $current_lsn,
    replay_timestamp: $replay_timestamp,
    timeline: ($timeline | tonumber),
    checked_at: $checked_at,
    status: (if $in_recovery then "standby" else "primary" end)
  }' > "${state_file}.tmp"
chmod 0644 "${state_file}.tmp"
mv "${state_file}.tmp" "$state_file"
