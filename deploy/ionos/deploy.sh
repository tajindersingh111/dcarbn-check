#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/deploy/ionos/staging.env}"
cd "$ROOT_DIR"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
[[ -f "$ENV_FILE" ]] || fail "Missing $ENV_FILE. Copy staging.env.example and populate it."

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
: "${STAGING_DOMAIN:?STAGING_DOMAIN is required}"
: "${ACME_EMAIL:?ACME_EMAIL is required}"
: "${RELEASE_SHA:?RELEASE_SHA is required}"
: "${MIGRATION_TARGET:?MIGRATION_TARGET is required}"
: "${MIGRATION_PHASE:?MIGRATION_PHASE is required}"
[[ "${MIGRATION_APPROVED:-false}" == "true" ]] || fail "MIGRATION_APPROVED must be true."
[[ "$RELEASE_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "RELEASE_SHA must be an exact 40-character SHA."
[[ "$MIGRATION_PHASE" =~ ^(expand|backfill|contract)$ ]] || fail "Invalid MIGRATION_PHASE."

required_secrets=(secret_key mfa_encryption_key database_url redis_url smtp_password postgres_password redis_password)
for secret in "${required_secrets[@]}"; do
  [[ -s "secrets/$secret" ]] || fail "Missing or empty secrets/$secret"
done
chmod 700 secrets
chmod 600 secrets/*

compose=(docker compose --env-file "$ENV_FILE" -f docker-compose.staging.yml)
mkdir -p deploy/evidence
chmod 700 deploy/evidence
"${compose[@]}" --profile operations config --quiet

if docker image inspect dcarbn-backend:staging-current >/dev/null 2>&1; then
  docker tag dcarbn-backend:staging-current dcarbn-backend:staging-previous
fi
if docker image inspect dcarbn-frontend:staging-current >/dev/null 2>&1; then
  docker tag dcarbn-frontend:staging-current dcarbn-frontend:staging-previous
fi

"${compose[@]}" build --pull backend frontend
"${compose[@]}" up -d postgres redis

if [[ "$MIGRATION_PHASE" == "contract" ]]; then
  "${compose[@]}" stop backend >/dev/null 2>&1 || true
  if "${compose[@]}" ps --status running --services | grep -qx backend; then
    fail "Old backend replicas are still running; contract migration blocked."
  fi
  export OLD_REPLICAS_RETIRED=true
else
  export OLD_REPLICAS_RETIRED=false
fi

"${compose[@]}" --profile operations run --rm migration
[[ -s deploy/evidence/migration.json ]] || fail "Migration evidence was not produced."
python3 - <<'PY'
import json
from pathlib import Path

evidence = json.loads(Path("deploy/evidence/migration.json").read_text())
if evidence.get("status") != "succeeded":
    raise SystemExit("Migration evidence does not record success.")
PY

"${compose[@]}" up -d --remove-orphans backend frontend gateway caddy
"${compose[@]}" ps

ENV_FILE="$ENV_FILE" "$ROOT_DIR/deploy/ionos/health-check.sh"
printf 'IONOS staging deployment is healthy at https://%s\n' "$STAGING_DOMAIN"
