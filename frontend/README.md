# D-carbN Frontend

Next.js frontend connected to the live FastAPI carbon-platform APIs.

## Workflows

- Dashboard summary
- Organisation creation and listing
- Reporting-period and inventory creation
- Scope 1, 2 and 3 activity entry
- DATa review start, decision and conversion
- Inventory approval requests, decisions and locking
- Audit-report generation, listing and payload retrieval

## Development

```bash
npm install
cp .env.example .env.local
npm run dev
```

Store a valid backend JWT in:

```text
localStorage["dcarbn.access_token"]
```

A development token may be supplied through
`NEXT_PUBLIC_DEV_ACCESS_TOKEN`. Do not use that variable in production.

## Validation

```bash
npm run typecheck
npm run lint
npm run build
```

## End-to-end tests

Deterministic browser workflow tests intercept the API at the network
boundary while preserving the real request paths and payload contracts:

```bash
npx playwright install chromium
npm run test:e2e
```

Run the additional live-backend smoke test by supplying:

```bash
E2E_ACCESS_TOKEN=<valid-jwt> npm run test:e2e:live
```

The live test calls the running FastAPI `/api/v1/dashboard` endpoint with
the configured bearer token.

## Session security

Browser authentication uses HTTP-only access and refresh cookies. The frontend
sends credentials on every API request and copies the `dcarbn_csrf` cookie into
the `X-CSRF-Token` header for state-changing requests.

Additional routes:

```text
/forgot-password
/reset-password
/settings/security
/admin/security-events
```
