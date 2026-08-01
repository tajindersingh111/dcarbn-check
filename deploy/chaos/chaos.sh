#!/usr/bin/env bash
set -Eeuo pipefail

scenario="${CHAOS_SCENARIO:-}"
duration="${CHAOS_DURATION_SECONDS:-60}"
compose_project="${COMPOSE_PROJECT_NAME:-dcarbn-carbon-platform-foundation}"
evidence_dir="${CHAOS_EVIDENCE_DIR:-/evidence}"

[[ -n "$scenario" ]] || {
  echo "CHAOS_SCENARIO is required." >&2
  exit 2
}
[[ "${CHAOS_CONFIRMATION:-}" == "CHAOS-D-CARBN" ]] || {
  echo "Set CHAOS_CONFIRMATION=CHAOS-D-CARBN." >&2
  exit 1
}

mkdir -p "$evidence_dir"
started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
result="passed"
detail=""

container_id() {
  docker ps \
    --filter "label=com.docker.compose.project=${compose_project}" \
    --filter "label=com.docker.compose.service=$1" \
    --format '{{.ID}}' |
    head -n 1
}

stop_for_duration() {
  local service="$1"
  local id
  id="$(container_id "$service")"
  [[ -n "$id" ]] || {
    echo "Container not found for service ${service}." >&2
    return 1
  }
  docker pause "$id"
  sleep "$duration"
  docker unpause "$id"
}

kill_and_restart() {
  local service="$1"
  local id
  id="$(container_id "$service")"
  [[ -n "$id" ]] || return 1
  docker kill "$id"
}

apply_latency() {
  local service="$1"
  local id
  id="$(container_id "$service")"
  [[ -n "$id" ]] || return 1
  docker exec "$id" tc qdisc add dev eth0 root netem \
    delay "${CHAOS_NETWORK_DELAY_MS:-500}ms" \
    "${CHAOS_NETWORK_JITTER_MS:-100}ms"
  sleep "$duration"
  docker exec "$id" tc qdisc del dev eth0 root || true
}

case "$scenario" in
  backend_pause)
    stop_for_duration backend || result="failed"
    ;;
  gateway_pause)
    stop_for_duration gateway || result="failed"
    ;;
  redis_restart)
    kill_and_restart redis || result="failed"
    sleep "$duration"
    ;;
  postgres_restart)
    kill_and_restart postgres || result="failed"
    sleep "$duration"
    ;;
  wal_shipping_pause)
    stop_for_duration postgres || result="failed"
    ;;
  backend_network_latency)
    apply_latency backend || result="failed"
    ;;
  regional_isolation)
    [[ "${CHAOS_ALLOW_REGIONAL_ISOLATION:-false}" == "true" ]] || {
      echo "Regional isolation requires CHAOS_ALLOW_REGIONAL_ISOLATION=true." >&2
      exit 1
    }
    hook="${CHAOS_REGIONAL_ISOLATION_HOOK:?Set CHAOS_REGIONAL_ISOLATION_HOOK}"
    "$hook" isolate
    trap '"$hook" restore' EXIT
    sleep "$duration"
    "$hook" restore
    trap - EXIT
    ;;
  *)
    echo "Unsupported chaos scenario: ${scenario}" >&2
    exit 2
    ;;
esac

ended_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
jq -n \
  --arg scenario "$scenario" \
  --arg started_at "$started_at" \
  --arg ended_at "$ended_at" \
  --arg result "$result" \
  --arg detail "$detail" \
  --argjson duration_seconds "$duration" \
  '{
    schema_version: 1,
    evidence_type: "chaos_exercise",
    scenario: $scenario,
    started_at: $started_at,
    ended_at: $ended_at,
    duration_seconds: $duration_seconds,
    result: $result,
    detail: $detail
  }' > "${evidence_dir}/chaos-${scenario}-${started_at//[:\-]/}.json"

[[ "$result" == "passed" ]]
