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

required_secrets=(secret_key mfa_encryption_key database_url redis_url smtp_password postgres_password redis_password)
for secret in "${required_secrets[@]}"; do
  [[ -s "secrets/$secret" ]] || fail "Missing or empty secrets/$secret"
done
chmod 700 secrets
chmod 600 secrets/*

compose=(docker compose --env-file "$ENV_FILE" -f docker-compose.staging.yml)
"${compose[@]}" config --quiet

if docker image inspect dcarbn-backend:staging-current >/dev/null 2>&1; then
  docker tag dcarbn-backend:staging-current dcarbn-backend:staging-previous
fi
if docker image inspect dcarbn-frontend:staging-current >/dev/null 2>&1; then
  docker tag dcarbn-frontend:staging-current dcarbn-frontend:staging-previous
fi

"${compose[@]}" build --pull backend frontend
"${compose[@]}" up -d --remove-orphans
"${compose[@]}" ps

ENV_FILE="$ENV_FILE" "$ROOT_DIR/deploy/ionos/health-check.sh"
printf 'IONOS staging deployment is healthy at https://%s\n' "$STAGING_DOMAIN"
