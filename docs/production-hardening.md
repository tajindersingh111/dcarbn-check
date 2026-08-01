# Production Hardening

## Request protection

The API applies Redis-backed fixed-window rate limits to:

- Login
- MFA verification and enrollment
- Refresh-token rotation
- Password recovery
- General API traffic

Rate-limit keys hash the policy and resolved client IP. Production fails closed
when Redis is unavailable. Liveness remains independent of Redis, while
readiness verifies both PostgreSQL and Redis.

## Account lockout

Known accounts maintain a rolling failed-login count. Repeated failures within
the configured window lock the account temporarily. Successful authentication
clears failure state. Tenant administrators can manually unlock an account.

Recommended starting values:

```env
ACCOUNT_LOCKOUT_THRESHOLD=5
ACCOUNT_FAILURE_WINDOW_MINUTES=15
ACCOUNT_LOCKOUT_MINUTES=30
```

Lockout does not replace IP rate limiting. Both protections are required to
reduce password spraying and targeted guessing risks.

## Proxy and client IP handling

Forwarded headers are trusted only when the direct peer matches
`TRUSTED_PROXY_IPS`. Configure this value to the gateway or load-balancer
network, not the public internet.

## Security headers

The backend and gateway add:

- Content-Security-Policy
- Strict-Transport-Security
- X-Content-Type-Options
- X-Frame-Options
- Referrer-Policy
- Permissions-Policy
- Cross-Origin-Opener-Policy
- Cross-Origin-Resource-Policy
- Cache-Control for API responses

The supplied frontend CSP permits inline scripts because the current Next.js
build has not been converted to per-request nonces. A nonce-based CSP is the
preferred next tightening step.

## Secrets

Settings support direct environment variables, `<SETTING>_FILE`, and mounted
files under `/run/secrets`. Production Compose mounts:

```text
secret_key
mfa_encryption_key
database_url
redis_url
smtp_password
postgres_password
```

The application validates production settings during startup and rejects
development secrets, insecure cookies, wildcard CORS, public documentation,
console email delivery, fail-open rate limiting, and HTTP frontend URLs.

## Containers

Production containers:

- Run as non-root users.
- Drop Linux capabilities.
- Enable `no-new-privileges`.
- Use read-only filesystems and bounded temporary filesystems.
- Define CPU, memory, process, and health limits.
- Keep PostgreSQL and Redis on an internal network.
- Expose only the gateway.
- Use multi-stage builds without backend development dependencies.

## TLS and gateway

`deploy/nginx.conf` expects TLS to terminate at an external load balancer or
ingress controller before traffic reaches port 8080. Preserve the original
scheme and client address through trusted forwarding headers.

Do not expose backend, frontend, PostgreSQL, or Redis ports directly in
production.

## Deployment sequence

```bash
mkdir -p secrets
cp deploy/production.env.example .env.production
chmod 600 secrets/*

docker compose \
  --env-file .env.production \
  -f docker-compose.production.yml \
  config

docker compose \
  --env-file .env.production \
  -f docker-compose.production.yml \
  build --pull

docker compose \
  --env-file .env.production \
  -f docker-compose.production.yml \
  up -d

docker compose \
  --env-file .env.production \
  -f docker-compose.production.yml \
  exec backend python -m app.cli.validate_production
```

Run database backups, restore drills, image scanning, dependency scanning, and
secret rotation through the deployment platform.
