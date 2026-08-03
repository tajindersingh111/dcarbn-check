#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/deploy/ionos/staging.env}"
cd "$ROOT_DIR"

[[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE" >&2; exit 1; }
docker image inspect dcarbn-backend:staging-previous >/dev/null 2>&1 || { echo "No previous backend image" >&2; exit 1; }
docker image inspect dcarbn-frontend:staging-previous >/dev/null 2>&1 || { echo "No previous frontend image" >&2; exit 1; }

docker tag dcarbn-backend:staging-previous dcarbn-backend:staging-current
docker tag dcarbn-frontend:staging-previous dcarbn-frontend:staging-current

compose=(docker compose --env-file "$ENV_FILE" -f docker-compose.staging.yml)
"${compose[@]}" up -d --no-build backend frontend gateway caddy
ENV_FILE="$ENV_FILE" "$ROOT_DIR/deploy/ionos/health-check.sh"

echo "Application images rolled back. Database migrations were not reversed."
