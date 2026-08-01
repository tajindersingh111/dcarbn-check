#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

usage() {
  echo "Usage: restore.sh <backup.dump.age> <manifest.json>" >&2
  exit 2
}

[[ $# -eq 2 ]] || usage
backup_file="$1"
manifest_file="$2"
[[ -f "$backup_file" && -f "$manifest_file" ]] || usage

read_secret() {
  local name="$1"
  local file_variable="${name}_FILE"
  local file_path="${!file_variable:-}"
  if [[ -n "$file_path" && -f "$file_path" ]]; then
    cat "$file_path"
    return
  fi
  local direct="${!name:-}"
  [[ -n "$direct" ]] || {
    echo "Required secret $name is unavailable." >&2
    exit 1
  }
  printf '%s' "$direct"
}

database_url="$(read_secret DATABASE_URL)"
identity_file="${BACKUP_AGE_IDENTITY_FILE:-/run/secrets/backup_age_identity}"
expected_checksum="$(jq -r '.sha256' "$manifest_file")"
actual_checksum="$(sha256sum "$backup_file" | awk '{print $1}')"

[[ "$expected_checksum" == "$actual_checksum" ]] || {
  echo "Backup checksum verification failed." >&2
  exit 1
}

[[ "${RESTORE_CONFIRMATION:-}" == "RESTORE-D-CARBN" ]] || {
  echo "Set RESTORE_CONFIRMATION=RESTORE-D-CARBN to proceed." >&2
  exit 1
}

working="$(mktemp -d)"
trap 'rm -rf "$working"' EXIT
dump="${working}/restore.dump"

age --decrypt --identity "$identity_file" --output "$dump" "$backup_file"
pg_restore --list "$dump" >/dev/null

if [[ "${RESTORE_CLEAN_DATABASE:-false}" == "true" ]]; then
  pg_restore \
    --dbname="$database_url" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    --exit-on-error \
    "$dump"
else
  pg_restore \
    --dbname="$database_url" \
    --no-owner \
    --no-privileges \
    --exit-on-error \
    "$dump"
fi

echo "Restore completed successfully."
