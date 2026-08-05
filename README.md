# D-carbN Carbon Platform

Standalone, multi-tenant Scope 1, Scope 2, and Scope 3 carbon-accounting platform foundation.

## Current foundation

- FastAPI backend
- PostgreSQL with SQLAlchemy 2 and Alembic
- JWT claim validation
- Tenant-scoped organisation APIs
- Initial inventory-domain entities
- Versioned organisational boundaries
- Operational-control, financial-control and equity-share consolidation
- Effective-dated legal-entity boundary memberships
- Versioned UK 2026 emission-factor registry
- Exact-schema flat-workbook importer with SHA-256 idempotency
- Factor-set approval and supersession workflow
- Searchable factor API with Decimal-preserved values
- Central Decimal-based unit-normalisation registry
- Deterministic approved-factor resolution with ambiguity safeguards
- Persisted factor-resolution lineage and warnings
- Versioned tenant-scoped activity records
- Immutable calculation runs and detailed calculation results
- Scope 1, Scope 2 and initial logistics-focused Scope 3 activity support
- Scope and category summaries in kgCO2e and tCO2e
- Versioned DATa integration API for vehicles, shipments, journeys, fuel and payload
- Operational-emissions imports with preserved methodology and lineage
- Idempotent batch processing, row-level errors and reconciliation
- Separate suggested and confirmed corporate classifications
- Controlled DATa operational-emissions review queue
- Reviewer approval and rejection workflow
- Immutable external operational-result calculation conversion
- Idempotent conversion with preserved DATa lineage
- Independent inventory approval workflow and control checks
- Immutable inventory locking
- Governed restatement and supersession workflow
- Hash-stamped audit-ready inventory reports
- Branded responsive Next.js workflow shell
- Organisation, inventory and activity-entry screens
- DATa review, inventory approval and audit-report workflows
- Central design tokens with Lato typography
- Live frontend API queries and mutations for every workflow
- Dashboard, inventory, approval and report read APIs
- Playwright browser workflow and live-backend smoke tests
- Argon2id authentication with rotating refresh sessions
- Tenant-scoped users, memberships and role administration
- Time-limited invitations and account activation
- Platform-admin tenant onboarding
- HTTP-only cookie sessions with CSRF protection
- TOTP MFA and single-use recovery codes
- Password recovery and transactional email delivery
- Tenant-scoped security-event monitoring
- Redis-backed endpoint and IP rate limiting
- Progressive account lockout with administrator unlock
- CSP, HSTS, trusted-host and proxy-aware security middleware
- Docker-secret and mounted-file secret loading
- Hardened non-root production containers and gateway deployment
- Encrypted scheduled PostgreSQL backups with retention and remote-copy support
- Isolated restore drills and disaster-recovery runbooks
- Prometheus, Grafana, Loki, Tempo, and OpenTelemetry observability
- Alertmanager rules for availability, security, backups, and infrastructure
- Continuous encrypted PostgreSQL WAL archiving to two regions
- Physical base backups and automated point-in-time recovery preparation
- Archive-fed warm standby deployment and controlled regional promotion
- Fencing, routing hooks, failback controls, and split-brain runbooks
- Automated regional failover exercises with measured RPO and RTO
- Controlled chaos scenarios and evidence capture
- Prometheus SLO recording rules and multi-window burn-rate alerts
- Signed release evidence and release-blocking assurance gates
- SPDX and CycloneDX SBOM generation for application images
- Grype, Trivy, dependency, secret, and license policy enforcement
- Keyless Cosign image signing and verification
- SLSA provenance attestations and digest-pinned release controls
- Kyverno and Gatekeeper production admission-policy examples
- Kustomize staging, primary-production, and standby-production overlays
- Argo CD projects, applications, drift correction, and GitOps promotion
- Argo Rollouts canaries with Prometheus analysis and automated rollback
- Kubernetes workload, network, storage, secret, and disruption controls
- Structured JSON logging
- React/Next.js frontend
- Lato typography and centralized brand tokens
- Docker Compose
- Pytest tests
- GitHub Actions CI

## Prerequisites

- Docker Desktop or Docker Engine with Compose
- Make, optional

## Start locally

```bash
cp .env.example .env
docker compose up --build
```

Backend API documentation:

- http://localhost:8000/docs
- http://localhost:8000/redoc

Frontend:

- http://localhost:3000

## Database migration

```bash
docker compose exec backend alembic upgrade head
```

## Initial administrator bootstrap

After applying database migrations to an empty environment, create the first tenant
and platform administrator once:

```bash
docker compose exec backend python -m app.scripts.bootstrap_platform_admin \
  --tenant-name "D-carbN Administration" \
  --tenant-slug dcarbn-admin \
  --email admin@example.com \
  --full-name "Initial Administrator"
```

The command prompts for the password without echoing it, refuses to run once a
platform administrator exists, and creates the initial tenant membership. Use a
protected `--password-file` only for controlled automation and remove it immediately
afterwards.

The local JWT generator is development tooling for existing database identities;
it is not an account-bootstrap mechanism. Production adoption still requires an
approved managed identity-provider decision or a formally accepted self-hosted
identity risk.

## Test

```bash
docker compose exec backend pytest
```

## Repository structure

```text
backend/        FastAPI application and migrations
frontend/       Next.js application and design system
infrastructure/ Deployment notes and future IaC
.github/         Continuous integration
```

## Pre-staging acceptance

Before the first staging deployment, use:

- `docs/uat/staging-uat-plan.md` for role-based acceptance and evidence.
- `docs/uat/test-data-plan.md` and `docs/uat/fixtures/` for fictional test data.
- `docs/operations/staging-handover-checklist.md` for infrastructure and operational handover.

The fixture files are contract-tested in CI and contain no customer or production data.

## Next implementation slice

1. Select and integrate the managed production identity provider.
2. Run live staging user-acceptance, accessibility and recovery tests.
3. Complete an independent penetration test before production launch.


## Hardened production deployment

```bash
cp deploy/production.env.example .env.production
mkdir -p secrets
# Populate the files documented in deploy/secrets/README.md.
chmod 600 secrets/*

docker compose \
  --env-file .env.production \
  -f docker-compose.production.yml \
  config

docker compose \
  --env-file .env.production \
  -f docker-compose.production.yml \
  up --build -d
```

Production startup rejects unsafe cookie, CORS, documentation, email, Redis,
rate-limit, URL, and secret settings. See
`docs/production-hardening.md` for the deployment checklist.


## Backup and observability deployment

```bash
docker compose \
  --env-file .env.production \
  -f docker-compose.production.yml \
  -f docker-compose.observability.yml \
  up --build -d
```

Operational status is available at:

```text
GET /api/v1/health/operational
```

Runbooks are stored under `runbooks/`. Backup and recovery architecture is
documented in `docs/observability-backup-and-disaster-recovery.md`.


## WAL archiving and regional recovery

Primary-region services:

```bash
docker compose   --env-file .env.production   -f docker-compose.production.yml   up --build -d postgres pitr-base-backup primary-region-status
```

Bootstrap the standby region:

```bash
STANDBY_PREPARE_CONFIRMATION=PREPARE-STANDBY-D-CARBN docker compose   --env-file .env.standby   -f docker-compose.region-standby.yml   --profile standby-bootstrap   run --rm standby-prepare

docker compose   --env-file .env.standby   -f docker-compose.region-standby.yml   up -d standby-postgres standby-redis failover-status
```

Recovery readiness is exposed at:

```text
GET /api/v1/health/recovery-readiness
```

See `docs/wal-pitr-and-cross-region-failover.md` and the regional recovery
runbooks before enabling provider-specific fencing and routing hooks.


## Software supply-chain assurance

The CI workflow in `.github/workflows/supply-chain.yml` builds the backend and
frontend images, creates SPDX and CycloneDX SBOMs, scans for vulnerabilities and
secrets, evaluates dependency and license policies, signs images with Cosign,
publishes provenance, and generates release evidence.

Verify a digest-pinned image locally:

```bash
SUPPLY_CHAIN_IMAGE=ghcr.io/example/dcarbn-backend@sha256:<digest> \
docker compose \
  -f docker-compose.production.yml \
  -f docker-compose.resilience.yml \
  --profile supply-chain \
  run --rm supply-chain-verifier
```

The release gate requires `supply-chain-release.json` in the
`supply_chain_evidence` volume. See
`docs/software-supply-chain-security.md`.


## Kubernetes and GitOps

Render the deployment overlays:

```bash
kustomize build deploy/kubernetes/overlays/staging
kustomize build deploy/kubernetes/overlays/production-primary
kustomize build deploy/kubernetes/overlays/production-standby
```

Bootstrap Argo CD resources:

```bash
kubectl apply -k deploy/gitops/argocd
```

Policy bundles are located under `deploy/policies/`. Production promotion is
performed by updating immutable image digests through
`deploy/progressive-delivery/promote-release.py`.

See `docs/kubernetes-gitops-progressive-delivery.md`.
