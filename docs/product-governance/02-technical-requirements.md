# Technical requirements document (TRD)

## Architecture baseline

- Frontend: Next.js 16, React 18, TypeScript, Lato.
- API: FastAPI on Python 3.12 with Pydantic.
- Persistence: PostgreSQL 16, SQLAlchemy 2, Alembic.
- Runtime services: Redis, containerised frontend/backend/gateway.
- Testing: Pytest, Ruff, mypy, ESLint, TypeScript and Playwright.
- Operations: Prometheus, Grafana, Loki, Tempo and OpenTelemetry.
- Delivery: GitHub Actions, containers, Kubernetes/Kustomize, Argo CD/Rollouts.
- Supply chain: SBOM, vulnerability/secret/license policy, Cosign signatures and provenance.

## API requirements

- All customer APIs use the versioned `/api/v1` boundary.
- OpenAPI is available only where explicitly enabled.
- JSON errors are safe, correlated and free of secrets.
- Mutating import/synchronisation operations support deterministic idempotency.
- Pagination, filtering and stable ordering apply to list endpoints.
- API contracts preserve Decimal precision and explicit units.
- Breaking changes require a new version or a documented migration period.

## Authentication and authorisation

Implemented self-hosted controls include Argon2id passwords, rotating HTTP-only refresh sessions, CSRF protection, TOTP MFA, single-use recovery codes, invitations, recovery, rate limiting, lockout and security-event monitoring. Production launch requires either:
1. approved managed identity-provider integration; or
2. formal acceptance of the self-hosted identity risk and operating model.

Every protected request resolves user, tenant, membership and roles. Database/service queries must independently filter by tenant; UI visibility is not an authorisation control.

## Integration requirements

QuickBooks, Xero and Sage use vendor-approved OAuth 2 flows and callback URLs. Direct APIs use approved secret-manager references. Provider tokens/keys never appear in application tables, logs, diagnostics or audit metadata. Connections require external company identity, mapping-profile version and lifecycle state. Synchronisation identities bind tenant, customer, provider, company, mapping version, cursor and requested time window.

## Calculation integrity

- Decimal arithmetic only for governed calculations.
- Effective-dated factor and methodology versions.
- Immutable calculation runs and approved inventory snapshots.
- SHA-256 identities for import payloads and synchronisation requests.
- Explicit allocation method and lifecycle boundary for Scope 3.
- No accounting record directly creates an approved emissions result.

## Security and privacy

TLS, secure cookies, CSP, HSTS, trusted hosts, restricted CORS, proxy awareness, non-root containers, encrypted secrets and least-privilege network/database access are mandatory. Complete threat modelling, DPIA/ROPA where applicable, retention schedule, data-subject workflow, vulnerability SLAs and an independent penetration test before production.

## Payments

No payment processor is currently implemented. Commercial launch may begin with invoice-led contracting. If self-service billing is approved, add a PCI-minimising hosted checkout, webhook verification, subscription/entitlement tables, tax/VAT handling, failed-payment workflows and audit events; never store card data.

## Reliability and release

Production must define measured SLOs, alert ownership, escalation, backup retention, restore evidence, RPO/RTO, regional failover responsibility and maintenance windows. Releases require green CI/security gates, migration rehearsal, rollback procedure, signed immutable image digests and release evidence.

## Environment and configuration

Separate development, test, staging, primary production and standby production environments. No production customer data in lower environments. Configuration is environment-specific; secrets are mounted or retrieved from an approved provider. Production startup rejects unsafe settings.
