#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

source_path="${1:?WAL source path is required}"
wal_name="${2:?WAL segment name is required}"
archive_root="${WAL_ARCHIVE_LOCAL_DIR:-/wal-archive}"
status_root="${WAL_ARCHIVE_STATUS_DIR:-/wal-status}"
region="${DCARBN_REGION:-primary}"
remote="${WAL_ARCHIVE_REMOTE:-}"
secondary_remote="${WAL_ARCHIVE_SECONDARY_REMOTE:-}"
recipient_file="${BACKUP_AGE_RECIPIENT_FILE:-/run/secrets/backup_age_recipient}"

[[ -f "$source_path" ]] || {
  echo "WAL source does not exist: $source_path" >&2
  exit 1
}
[[ -s "$recipient_file" ]] || {
  echo "Age recipient is unavailable." >&2
  exit 1
}

mkdir -p "$archive_root" "$status_root"
encrypted="${archive_root}/${wal_name}.age"
manifest="${archive_root}/${wal_name}.json"
temporary="${encrypted}.tmp"

if [[ -f "$encrypted" && -f "$manifest" ]]; then
  exit 0
fi

recipient="$(cat "$recipient_file")"
age --encrypt \
  --recipient "$recipient" \
  --output "$temporary" \
  "$source_path"

checksum="$(sha256sum "$temporary" | awk '{print $1}')"
size_bytes="$(stat -c '%s' "$temporary")"
archived_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

mv "$temporary" "$encrypted"

jq -n \
  --arg wal_name "$wal_name" \
  --arg archived_at "$archived_at" \
  --arg sha256 "$checksum" \
  --arg region "$region" \
  --argjson size_bytes "$size_bytes" \
  '{
    wal_name: $wal_name,
    archived_at: $archived_at,
    sha256: $sha256,
    size_bytes: $size_bytes,
    encrypted: true,
    region: $region
  }' > "${manifest}.tmp"
chmod 0644 "${manifest}.tmp"
mv "${manifest}.tmp" "$manifest"

copy_remote() {
  local target="$1"
  [[ -n "$target" ]] || return 0
  rclone copyto "$encrypted" "${target%/}/wal/${wal_name}.age"
  rclone copyto "$manifest" "${target%/}/wal/${wal_name}.json"
}

copy_remote "$remote"
copy_remote "$secondary_remote"

jq -n \
  --arg wal_name "$wal_name" \
  --arg archived_at "$archived_at" \
  --arg region "$region" \
  '{
    status: "ok",
    latest_wal: $wal_name,
    latest_archived_at: $archived_at,
    region: $region
  }' > "${status_root}/wal-status.json.tmp"
chmod 0644 "${status_root}/wal-status.json.tmp"
mv "${status_root}/wal-status.json.tmp" \
  "${status_root}/wal-status.json"

exit 0
