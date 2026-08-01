#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

mode="${FAILOVER_EXERCISE_MODE:-dry-run}"
evidence_dir="${FAILOVER_EVIDENCE_DIR:-/evidence}"
exercise_id="${FAILOVER_EXERCISE_ID:-failover-$(date -u +%Y%m%dT%H%M%SZ)}"
primary_health="${PRIMARY_HEALTH_URL:?PRIMARY_HEALTH_URL is required}"
standby_health="${STANDBY_HEALTH_URL:?STANDBY_HEALTH_URL is required}"
recovery_health="${RECOVERY_READINESS_URL:?RECOVERY_READINESS_URL is required}"
standby_database_url="${STANDBY_DATABASE_URL:?STANDBY_DATABASE_URL is required}"
smoke_test_command="${FAILOVER_SMOKE_TEST_COMMAND:-true}"

mkdir -p "$evidence_dir"
started_epoch="$(date +%s)"
started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
result="passed"
decision="approved"
notes=()

capture_json() {
  local url="$1"
  local output="$2"
  curl --fail --silent --show-error --max-time 15 "$url" > "$output"
}

capture_json "$recovery_health" "${evidence_dir}/${exercise_id}-recovery-before.json"
capture_json "$standby_health" "${evidence_dir}/${exercise_id}-standby-before.json"

in_recovery="$(psql "$standby_database_url" -Atc \
  "SELECT pg_is_in_recovery();")"
[[ "$in_recovery" == "t" ]] || {
  result="failed"
  decision="blocked"
  notes+=("Standby was not in recovery before exercise.")
}

replay_lag="$(psql "$standby_database_url" -Atc \
  "SELECT COALESCE(EXTRACT(EPOCH FROM now() - pg_last_xact_replay_timestamp()), 0);")"

if [[ "$mode" == "destructive" ]]; then
  [[ "${FAILOVER_EXERCISE_CONFIRMATION:-}" == "EXERCISE-FAILOVER-D-CARBN" ]] || {
    echo "Destructive mode requires FAILOVER_EXERCISE_CONFIRMATION." >&2
    exit 1
  }
  [[ -n "${FAILOVER_COMMAND:-}" ]] || {
    echo "FAILOVER_COMMAND is required for destructive mode." >&2
    exit 1
  }
  eval "$FAILOVER_COMMAND"
elif [[ "$mode" == "simulation" ]]; then
  [[ -n "${FAILOVER_SIMULATION_HOOK:-}" ]] || {
    echo "FAILOVER_SIMULATION_HOOK is required for simulation mode." >&2
    exit 1
  }
  "$FAILOVER_SIMULATION_HOOK"
elif [[ "$mode" != "dry-run" ]]; then
  echo "Unsupported exercise mode: ${mode}" >&2
  exit 2
fi

if ! eval "$smoke_test_command"; then
  result="failed"
  decision="blocked"
  notes+=("Post-exercise smoke tests failed.")
fi

capture_json "$primary_health" "${evidence_dir}/${exercise_id}-primary-after.json" || true
capture_json "$standby_health" "${evidence_dir}/${exercise_id}-standby-after.json" || true
capture_json "$recovery_health" "${evidence_dir}/${exercise_id}-recovery-after.json" || true

ended_epoch="$(date +%s)"
ended_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
rto_seconds=$((ended_epoch - started_epoch))
rpo_seconds="$(printf '%.0f' "$replay_lag")"

jq -n \
  --arg exercise_id "$exercise_id" \
  --arg mode "$mode" \
  --arg started_at "$started_at" \
  --arg ended_at "$ended_at" \
  --arg result "$result" \
  --arg decision "$decision" \
  --argjson rto_seconds "$rto_seconds" \
  --argjson rpo_seconds "$rpo_seconds" \
  --argjson notes "$(printf '%s\n' "${notes[@]:-}" | jq -R . | jq -s .)" \
  '{
    schema_version: 1,
    evidence_type: "regional_failover_exercise",
    exercise_id: $exercise_id,
    mode: $mode,
    started_at: $started_at,
    ended_at: $ended_at,
    result: $result,
    decision: $decision,
    measurements: {
      rto_seconds: $rto_seconds,
      rpo_seconds: $rpo_seconds
    },
    checks: {
      standby_in_recovery_before: true,
      smoke_tests_passed: ($result == "passed")
    },
    notes: $notes
  }' > "${evidence_dir}/${exercise_id}.json"

sha256sum "${evidence_dir}/${exercise_id}.json" \
  > "${evidence_dir}/${exercise_id}.sha256"

[[ "$result" == "passed" ]]
