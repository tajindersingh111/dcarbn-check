# Strict type-safety policy

## Policy

The backend is checked with MyPy in strict mode. Compliance-critical modules must
not use module-level `ignore_errors` overrides. This control applies to calculation,
factor resolution, inventory governance, governed ingestion and review, tenant and
identity enforcement, and their supporting operational middleware and services.

Type fixes must preserve calculation outputs, deterministic factor selection, API
contracts, tenant predicates, audit event content, and persisted lineage. A type
error must not be hidden with a broad `Any`, a blanket cast, a new MyPy exemption,
or an unexplained `# type: ignore` comment.

When an external library has an unavoidable typing defect, a line-specific
suppression is the last resort. It must identify the precise MyPy error code,
explain the external limitation on the same line, and have a focused regression
test that exercises the boundary. Reviewers must confirm that the suppression does
not weaken governed application data.

## Enforced modules

The policy specifically covers:

- `app.api.routes.identity`
- `app.auth.dependencies`
- `app.core.logging`
- `app.core.observability`
- `app.middleware.rate_limit`
- `app.middleware.security_headers`
- `app.services.activities`
- `app.services.boundaries`
- `app.services.calculations`
- `app.services.data_integration`
- `app.services.data_review`
- `app.services.email_delivery`
- `app.services.factor_resolution`
- `app.services.inventory_governance`
- `app.services.operational_health`
- `app.services.organisations`
- `app.services.session_auth`

The backend policy tests fail if strict mode is disabled, an `ignore_errors`
override is introduced, a governed module is removed, or a suppression lacks an
error code and explanation.

## Validation and review

Changes to governed modules require these checks from `backend/`:

```bash
mypy app
ruff check app tests
pytest
```

The portable suite uses SQLite and reports PostgreSQL-only skips separately. Before
approval, reviewers must inspect the final diff for changes to formulas, ranking or
fallback order, request and response schemas, tenant filters, audit records, and
lineage fields. Networked CI and supply-chain security remain exact-head merge
gates.
