#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACTS="${ROOT}/artifacts/pilot-validation"
mkdir -p "$ARTIFACTS"

status=0

run() {
  local name="$1"
  shift
  echo "==> ${name}"
  if "$@" >"${ARTIFACTS}/${name}.log" 2>&1; then
    printf 'passed\n' >"${ARTIFACTS}/${name}.status"
  else
    printf 'failed\n' >"${ARTIFACTS}/${name}.status"
    status=1
  fi
}

run python-syntax \
  python -m compileall -q "${ROOT}/backend/app" "${ROOT}/backend/tests"

run integration-contracts \
  python "${ROOT}/tools/validate_integration_contracts.py" \
    --root "$ROOT" \
    --output "${ARTIFACTS}/integration-contracts.json"

if python -c 'import aiosqlite, asyncpg, redis, ruff, mypy' >/dev/null 2>&1; then
  run backend-pytest \
    env PYTHONPATH="${ROOT}/backend" \
    pytest -q "${ROOT}/backend/tests"

  run backend-ruff \
    python -m ruff check "${ROOT}/backend/app" "${ROOT}/backend/tests"

  run backend-mypy \
    env PYTHONPATH="${ROOT}/backend" \
    python -m mypy "${ROOT}/backend/app"
else
  printf 'blocked: missing aiosqlite, asyncpg, redis, ruff, or mypy\n' \
    >"${ARTIFACTS}/backend-complete-suite.status"
  status=1
fi

if [[ -f "${ROOT}/frontend/package-lock.json" ]]; then
  (
    cd "${ROOT}/frontend"
    run frontend-install npm ci
    run frontend-typecheck npm run typecheck
    run frontend-lint npm run lint
    run frontend-build npm run build
    run frontend-e2e npm run test:e2e:all
  )
else
  printf 'blocked: frontend/package-lock.json is missing\n' \
    >"${ARTIFACTS}/frontend-complete-suite.status"
  status=1
fi

if command -v docker >/dev/null 2>&1; then
  run compose-production \
    docker compose -f "${ROOT}/docker-compose.production.yml" config
  run compose-observability \
    docker compose \
      -f "${ROOT}/docker-compose.production.yml" \
      -f "${ROOT}/docker-compose.observability.yml" config
else
  printf 'blocked: Docker is unavailable\n' \
    >"${ARTIFACTS}/container-validation.status"
  status=1
fi

if command -v kustomize >/dev/null 2>&1; then
  for overlay in staging production-primary production-standby; do
    run "kustomize-${overlay}" \
      kustomize build \
      "${ROOT}/deploy/kubernetes/overlays/${overlay}"
  done
else
  printf 'blocked: Kustomize is unavailable\n' \
    >"${ARTIFACTS}/kustomize-validation.status"
  status=1
fi

exit "$status"
