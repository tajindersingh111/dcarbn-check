#!/usr/bin/env bash
set -Eeuo pipefail

BACKUP_ROOT="${BACKUP_ROOT:-/backups}"
latest_manifest="$(find "$BACKUP_ROOT" -type f -name 'postgres-*.json' | sort | tail -n 1)"
[[ -n "$latest_manifest" ]] || {
  echo "No backup manifest exists." >&2
  exit 1
}

backup_file="${BACKUP_ROOT}/$(jq -r '.filename' "$latest_manifest")"
[[ -f "$backup_file" ]] || {
  echo "Backup file referenced by manifest does not exist." >&2
  exit 1
}

export RESTORE_CONFIRMATION=RESTORE-D-CARBN
export RESTORE_CLEAN_DATABASE=true
/usr/local/bin/restore.sh "$backup_file" "$latest_manifest"

psql "$(cat "${DATABASE_URL_FILE}")" \
  --set=ON_ERROR_STOP=1 \
  --command="SELECT count(*) AS tenant_count FROM tenants;" \
  --command="SELECT max(version_num) AS migration FROM alembic_version;"

echo "Restore drill validation completed."
