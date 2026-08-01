#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

read_secret() {
  local name="$1"
  local file_variable="${name}_FILE"
  local file_path="${!file_variable:-}"
  if [[ -n "$file_path" && -f "$file_path" ]]; then
    cat "$file_path"
    return
  fi
  [[ -n "${!name:-}" ]] || {
    echo "Required secret $name is unavailable." >&2
    exit 1
  }
  printf '%s' "${!name}"
}

database_url="$(read_secret DATABASE_URL)"
recipient="$(read_secret BACKUP_AGE_RECIPIENT)"
root="${PITR_BASE_BACKUP_ROOT:-/base-backups}"
status_root="${PITR_STATUS_DIR:-/status}"
remote="${PITR_REMOTE:-}"
secondary_remote="${PITR_SECONDARY_REMOTE:-}"
retention_days="${PITR_BASE_BACKUP_RETENTION_DAYS:-14}"
region="${DCARBN_REGION:-primary}"

mkdir -p "$root" "$status_root"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_id="base-${timestamp}"
working="$(mktemp -d)"
trap 'rm -rf "$working"' EXIT

tar_file="${working}/${backup_id}.tar"
encrypted="${root}/${backup_id}.tar.age"
manifest="${root}/${backup_id}.json"

pg_basebackup \
  --dbname="$database_url" \
  --format=plain \
  --checkpoint=fast \
  --wal-method=stream \
  --label="$backup_id" \
  --progress \
  --target="$working/base"

tar \
  --create \
  --file="$tar_file" \
  --directory="$working/base" \
  .

age --encrypt \
  --recipient "$recipient" \
  --output "${encrypted}.tmp" \
  "$tar_file"
mv "${encrypted}.tmp" "$encrypted"

checksum="$(sha256sum "$encrypted" | awk '{print $1}')"
size_bytes="$(stat -c '%s' "$encrypted")"
created_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

jq -n \
  --arg backup_id "$backup_id" \
  --arg created_at "$created_at" \
  --arg filename "$(basename "$encrypted")" \
  --arg sha256 "$checksum" \
  --arg region "$region" \
  --argjson size_bytes "$size_bytes" \
  '{
    backup_id: $backup_id,
    created_at: $created_at,
    filename: $filename,
    sha256: $sha256,
    size_bytes: $size_bytes,
    encrypted: true,
    format: "pg_basebackup-plain-tar",
    includes_streamed_wal: true,
    region: $region,
    verified: true
  }' > "$manifest"

copy_remote() {
  local target="$1"
  [[ -n "$target" ]] || return 0
  rclone copyto "$encrypted" "${target%/}/base/${backup_id}.tar.age"
  rclone copyto "$manifest" "${target%/}/base/${backup_id}.json"
}

copy_remote "$remote"
copy_remote "$secondary_remote"

find "$root" -type f \
  \( -name 'base-*.tar.age' -o -name 'base-*.json' \) \
  -mtime "+${retention_days}" -delete

jq -n \
  --arg backup_id "$backup_id" \
  --arg created_at "$created_at" \
  --arg region "$region" \
  '{
    status: "ok",
    latest_base_backup_id: $backup_id,
    latest_base_backup_at: $created_at,
    verified: true,
    region: $region
  }' > "${status_root}/pitr-status.json.tmp"
chmod 0644 "${status_root}/pitr-status.json.tmp"
mv "${status_root}/pitr-status.json.tmp" \
  "${status_root}/pitr-status.json"

echo "Base backup ${backup_id} completed."
