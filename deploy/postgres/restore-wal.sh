#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

wal_name="${1:?WAL segment name is required}"
destination="${2:?Restore destination is required}"
archive_root="${WAL_ARCHIVE_LOCAL_DIR:-/wal-archive}"
remote="${WAL_ARCHIVE_REMOTE:-}"
secondary_remote="${WAL_ARCHIVE_SECONDARY_REMOTE:-}"
identity_file="${BACKUP_AGE_IDENTITY_FILE:-/run/secrets/backup_age_identity}"

working="$(mktemp -d)"
trap 'rm -rf "$working"' EXIT

encrypted="${working}/${wal_name}.age"
manifest="${working}/${wal_name}.json"

fetch_from() {
  local target="$1"
  [[ -n "$target" ]] || return 1
  rclone copyto "${target%/}/wal/${wal_name}.age" "$encrypted" &&
    rclone copyto "${target%/}/wal/${wal_name}.json" "$manifest"
}

if [[ -f "${archive_root}/${wal_name}.age" ]]; then
  cp "${archive_root}/${wal_name}.age" "$encrypted"
  cp "${archive_root}/${wal_name}.json" "$manifest"
elif fetch_from "$remote"; then
  :
elif fetch_from "$secondary_remote"; then
  :
else
  exit 1
fi

expected="$(jq -r '.sha256' "$manifest")"
actual="$(sha256sum "$encrypted" | awk '{print $1}')"
[[ "$expected" == "$actual" ]] || {
  echo "WAL checksum verification failed for ${wal_name}." >&2
  exit 1
}

age --decrypt \
  --identity "$identity_file" \
  --output "$destination" \
  "$encrypted"
