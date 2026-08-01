#!/usr/bin/env bash
set -Eeuo pipefail

database_url="${DATABASE_URL:?DATABASE_URL is required}"

psql "$database_url" \
  --set=ON_ERROR_STOP=1 \
  --command="SELECT pg_is_in_recovery() AS in_recovery;" \
  --command="SELECT pg_last_wal_replay_lsn() AS replay_lsn;" \
  --command="SELECT max(version_num) AS migration FROM alembic_version;" \
  --command="SELECT count(*) AS tenants FROM tenants;" \
  --command="SELECT count(*) AS inventories FROM inventories;" \
  --command="SELECT count(*) AS audit_reports FROM audit_reports;"

echo "PITR validation completed."
