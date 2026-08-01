#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

[[ "${PITR_CONFIRMATION:-}" == "RECOVER-D-CARBN" ]] || {
  echo "Set PITR_CONFIRMATION=RECOVER-D-CARBN to proceed." >&2
  exit 1
}

target_dir="${PITR_TARGET_DIR:-/var/lib/postgresql/data}"
base_root="${PITR_BASE_BACKUP_ROOT:-/base-backups}"
remote="${PITR_REMOTE:-}"
secondary_remote="${PITR_SECONDARY_REMOTE:-}"
identity_file="${BACKUP_AGE_IDENTITY_FILE:-/run/secrets/backup_age_identity}"
target_time="${PITR_TARGET_TIME:-}"
target_lsn="${PITR_TARGET_LSN:-}"
target_xid="${PITR_TARGET_XID:-}"
target_name="${PITR_TARGET_NAME:-}"
target_timeline="${PITR_TARGET_TIMELINE:-latest}"
target_action="${PITR_TARGET_ACTION:-pause}"

set_count=0
for value in "$target_time" "$target_lsn" "$target_xid" "$target_name"; do
  [[ -n "$value" ]] && set_count=$((set_count + 1))
done
[[ "$set_count" -le 1 ]] || {
  echo "Configure only one PITR recovery target." >&2
  exit 1
}

working="$(mktemp -d)"
trap 'rm -rf "$working"' EXIT

stage_remote_manifests() {
  local source="$1"
  local destination="$2"
  [[ -n "$source" ]] || return 0
  mkdir -p "$destination"
  rclone copy "${source%/}/base" "$destination" \
    --include 'base-*.json' \
    --max-depth 1 \
    || true
}

select_manifest() {
  if [[ -n "${PITR_BASE_BACKUP_ID:-}" ]]; then
    printf '%s' "${PITR_BASE_BACKUP_ID}"
    return
  fi

  catalog="${working}/catalog"
  mkdir -p "$catalog"
  find "$base_root" -maxdepth 1 -name 'base-*.json' -type f \
    -exec cp {} "$catalog/" \; 2>/dev/null || true
  stage_remote_manifests "$remote" "$catalog"
  stage_remote_manifests "$secondary_remote" "$catalog"

  if [[ -n "$target_time" ]]; then
    normalized_target="$(date --utc --date="$target_time" +%Y-%m-%dT%H:%M:%SZ)"
    find "$catalog" -name 'base-*.json' -type f -print0 |
      xargs -0 -r jq -r \
        --arg target "$normalized_target" \
        'select(.created_at <= $target) | [.created_at, .backup_id] | @tsv' |
      sort |
      tail -n 1 |
      cut -f2
    return
  fi

  find "$catalog" -name 'base-*.json' -type f -print0 |
    xargs -0 -r jq -r '[.created_at, .backup_id] | @tsv' |
    sort |
    tail -n 1 |
    cut -f2
}

backup_id="$(select_manifest)"
[[ -n "$backup_id" ]] || {
  echo "No suitable base backup was found." >&2
  exit 1
}

manifest="${working}/${backup_id}.json"
encrypted="${working}/${backup_id}.tar.age"

fetch_remote() {
  local source="$1"
  [[ -n "$source" ]] || return 1
  rclone copyto "${source%/}/base/${backup_id}.json" "$manifest" &&
    rclone copyto "${source%/}/base/${backup_id}.tar.age" "$encrypted"
}

if [[ -f "${base_root}/${backup_id}.json" ]]; then
  cp "${base_root}/${backup_id}.json" "$manifest"
  cp "${base_root}/${backup_id}.tar.age" "$encrypted"
elif fetch_remote "$remote"; then
  :
elif fetch_remote "$secondary_remote"; then
  :
else
  echo "Base backup ${backup_id} could not be fetched." >&2
  exit 1
fi

expected="$(jq -r '.sha256' "$manifest")"
actual="$(sha256sum "$encrypted" | awk '{print $1}')"
[[ "$expected" == "$actual" ]] || {
  echo "Base-backup checksum verification failed." >&2
  exit 1
}

[[ ! -e "${target_dir}/PG_VERSION" ]] || {
  echo "PITR target directory is not empty." >&2
  exit 1
}

mkdir -p "$target_dir"
age --decrypt \
  --identity "$identity_file" \
  --output "${working}/base.tar" \
  "$encrypted"
tar --extract \
  --file="${working}/base.tar" \
  --directory="$target_dir"

cat >> "${target_dir}/postgresql.auto.conf" <<EOF
restore_command = '/usr/local/bin/restore-wal.sh %f %p'
recovery_target_timeline = '${target_timeline}'
recovery_target_action = '${target_action}'
EOF

[[ -n "$target_time" ]] &&
  printf "recovery_target_time = '%s'\n" "$target_time" \
    >> "${target_dir}/postgresql.auto.conf"
[[ -n "$target_lsn" ]] &&
  printf "recovery_target_lsn = '%s'\n" "$target_lsn" \
    >> "${target_dir}/postgresql.auto.conf"
[[ -n "$target_xid" ]] &&
  printf "recovery_target_xid = '%s'\n" "$target_xid" \
    >> "${target_dir}/postgresql.auto.conf"
[[ -n "$target_name" ]] &&
  printf "recovery_target_name = '%s'\n" "$target_name" \
    >> "${target_dir}/postgresql.auto.conf"

touch "${target_dir}/recovery.signal"
chmod 0700 "$target_dir"

jq -n \
  --arg backup_id "$backup_id" \
  --arg target_time "$target_time" \
  --arg target_lsn "$target_lsn" \
  --arg target_xid "$target_xid" \
  --arg target_name "$target_name" \
  --arg target_timeline "$target_timeline" \
  '{
    backup_id: $backup_id,
    target_time: ($target_time | if length > 0 then . else null end),
    target_lsn: ($target_lsn | if length > 0 then . else null end),
    target_xid: ($target_xid | if length > 0 then . else null end),
    target_name: ($target_name | if length > 0 then . else null end),
    target_timeline: $target_timeline,
    prepared_at: now | todateiso8601
  }' > "${target_dir}/dcarbn-recovery.json"

echo "PITR data directory prepared from ${backup_id}."
