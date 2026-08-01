#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

BACKUP_ROOT="${BACKUP_ROOT:-/backups}"
STATUS_FILE="${BACKUP_STATUS_FILE:-/status/backup-status.json}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-35}"
SCHEDULE_SECONDS="${BACKUP_SCHEDULE_SECONDS:-86400}"
RUN_ONCE="${BACKUP_RUN_ONCE:-false}"
VERIFY_RESTORE_LIST="${BACKUP_VERIFY_RESTORE_LIST:-true}"

read_secret() {
  local name="$1"
  local file_variable="${name}_FILE"
  local file_path="${!file_variable:-}"
  if [[ -n "$file_path" && -f "$file_path" ]]; then
    cat "$file_path"
    return
  fi
  local direct="${!name:-}"
  if [[ -n "$direct" ]]; then
    printf '%s' "$direct"
    return
  fi
  echo "Required secret $name is unavailable." >&2
  exit 1
}

database_url="$(read_secret DATABASE_URL)"
age_recipient="$(read_secret BACKUP_AGE_RECIPIENT)"

mkdir -p "$BACKUP_ROOT" "$(dirname "$STATUS_FILE")"

write_status() {
  local success="$1"
  local backup_id="$2"
  local verified="$3"
  local detail="$4"
  local timestamp
  timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  local previous_success=""
  if [[ -f "$STATUS_FILE" ]]; then
    previous_success="$(jq -r '.latest_success_at // empty' "$STATUS_FILE")"
  fi
  jq -n \
    --argjson success "$success" \
    --arg backup_id "$backup_id" \
    --argjson verified "$verified" \
    --arg detail "$detail" \
    --arg timestamp "$timestamp" \
    --arg previous_success "$previous_success" \
    '{
      success: $success,
      backup_id: $backup_id,
      verified: $verified,
      detail: $detail,
      latest_attempt_at: $timestamp
    } + (
      if $success then
        {latest_success_at: $timestamp}
      elif $previous_success != "" then
        {latest_success_at: $previous_success}
      else
        {}
      end
    )' \
    > "${STATUS_FILE}.tmp"
  chmod 0644 "${STATUS_FILE}.tmp"
  mv "${STATUS_FILE}.tmp" "$STATUS_FILE"
}

perform_backup() {
  local timestamp backup_id working dump encrypted manifest checksum
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  backup_id="postgres-${timestamp}"
  working="$(mktemp -d)"
  dump="${working}/${backup_id}.dump"
  encrypted="${BACKUP_ROOT}/${backup_id}.dump.age"
  manifest="${BACKUP_ROOT}/${backup_id}.json"

  cleanup() {
    rm -rf "$working"
  }
  trap cleanup RETURN

  echo "Creating PostgreSQL backup ${backup_id}."
  if ! pg_dump \
      --dbname="$database_url" \
      --format=custom \
      --compress=9 \
      --no-owner \
      --no-privileges \
      --file="$dump"; then
    write_status false "$backup_id" false "pg_dump failed"
    return 1
  fi

  if [[ "$VERIFY_RESTORE_LIST" == "true" ]]; then
    if ! pg_restore --list "$dump" >/dev/null; then
      write_status false "$backup_id" false "pg_restore list verification failed"
      return 1
    fi
  fi

  age --encrypt --recipient "$age_recipient" --output "$encrypted" "$dump"
  checksum="$(sha256sum "$encrypted" | awk '{print $1}')"

  jq -n \
    --arg backup_id "$backup_id" \
    --arg created_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg filename "$(basename "$encrypted")" \
    --arg sha256 "$checksum" \
    --arg postgres_version "$(pg_dump --version)" \
    '{
      backup_id: $backup_id,
      created_at: $created_at,
      filename: $filename,
      sha256: $sha256,
      encrypted: true,
      format: "postgres-custom",
      verified: true,
      postgres_version: $postgres_version
    }' > "$manifest"

  if [[ -n "${BACKUP_REMOTE:-}" ]]; then
    rclone copy "$encrypted" "$BACKUP_REMOTE"
    rclone copy "$manifest" "$BACKUP_REMOTE"
  fi

  find "$BACKUP_ROOT" -type f \
    \( -name 'postgres-*.dump.age' -o -name 'postgres-*.json' \) \
    -mtime "+${RETENTION_DAYS}" -delete

  write_status true "$backup_id" true "backup completed"
  echo "Backup ${backup_id} completed."
}

while true; do
  if ! perform_backup; then
    echo "Backup attempt failed." >&2
  fi
  if [[ "$RUN_ONCE" == "true" ]]; then
    exit 0
  fi
  sleep "$SCHEDULE_SECONDS"
done
