# Railway production-branch deployment

This branch contains the full D-carbN Carbon Platform. The root pilot-only
`railway.json` has been removed so Railway cannot silently deploy
`local-demo` through `Dockerfile.railway-pilot`.

Railway does not run this repository's Docker Compose stack as a single service.
Deploy the frontend, backend, PostgreSQL, and Redis as separate services in one
Railway project.

## Branch

Use:

```text
agent/railway-production
```

Do not deploy the repository root as a single service.

## Frontend service

- Source repository: `Leonardfraser/Dcarbn-Scope-1-2`
- Branch: `agent/railway-production`
- Root Directory: `/frontend`
- Config File Path: `/frontend/railway.json`
- Public domain: required
- Build and runtime variable:
  - `NEXT_PUBLIC_API_BASE_URL=https://<backend-domain>/api/v1`
  - `NEXT_PUBLIC_APP_ENV=staging`

The API URL is compiled into the Next.js browser bundle, so set it before the
frontend build.

## Backend service

- Source repository: `Leonardfraser/Dcarbn-Scope-1-2`
- Branch: `agent/railway-production`
- Root Directory: `/backend`
- Config File Path: `/backend/railway.json`
- Public domain: required when the browser calls the API directly
- Health endpoint: `/api/v1/health/live`
- Readiness endpoint: `/api/v1/health/ready`

The service config runs `alembic upgrade head` as a pre-deploy command and
starts Uvicorn on Railway's `PORT`.

## Managed data services

Add Railway-managed PostgreSQL and Redis services to the same Railway project.

Set the backend `DATABASE_URL` using PostgreSQL reference variables, but retain
the async SQLAlchemy scheme:

```text
postgresql+asyncpg://<user>:<password>@<private-host>:<port>/<database>
```

Set `REDIS_URL` from the Redis service's Railway reference variable. Keep
database and Redis traffic on Railway private networking.

## Required backend staging variables

Supply protected values in Railway; never commit secret values:

```text
APP_ENV=staging
SECRET_KEY=<at-least-32-random-characters>
MFA_ENCRYPTION_KEY=<at-least-32-random-characters>
DATABASE_URL=<async-postgresql-url>
REDIS_URL=<railway-redis-url>
DATABASE_CONNECTION_LIMIT=<hosting-limit>
FRONTEND_BASE_URL=https://<frontend-domain>
CORS_ORIGINS=https://<frontend-domain>
TRUSTED_HOSTS=<backend-hostname>
COOKIE_SECURE=true
COOKIE_SAMESITE=none
HSTS_ENABLED=true
DOCS_ENABLED=false
EXPOSE_TOKENS_IN_API=false
REDIS_REQUIRED=true
RATE_LIMIT_FAIL_OPEN=false
EMAIL_PROVIDER=smtp
EMAIL_FROM_ADDRESS=<approved-address>
SMTP_HOST=<approved-host>
SMTP_PORT=<approved-port>
SMTP_USERNAME=<approved-user>
SMTP_PASSWORD=<protected-secret>
SMTP_USE_TLS=true
```

For a same-origin gateway or app/API subdomains sharing the approved cookie
domain, review whether `COOKIE_SAMESITE=strict` can be restored.

## Deployment order

1. Provision PostgreSQL and Redis.
2. Configure and deploy the backend.
3. Confirm migrations completed.
4. Verify `/api/v1/health/live` and `/api/v1/health/ready`.
5. Configure and deploy the frontend with the final backend API URL.
6. Bootstrap the initial platform administrator using the repository command.
7. Verify login and tenant access.
8. Test with fictional or irreversibly anonymised CSV files only.
9. Confirm uploaded records persist after refresh and in a separate browser.
10. Move the public production URL only after all checks pass.

## Acceptance signals

The correct deployment must:

- show the page title `D-carbN Carbon Platform`;
- omit the `Browser-local pilot` banner;
- omit the prototype role selector;
- authenticate through the backend;
- persist uploads in PostgreSQL;
- return healthy backend liveness and readiness responses.

Do not upload real New Era customer, employee, or commercially sensitive data
until the staging controls and customer-data handling protocol are approved.
