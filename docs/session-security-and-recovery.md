# Session Security, MFA, Recovery and Monitoring

## Cookie sessions

Browser sessions use three cookies:

- `dcarbn_access`: short-lived, HTTP-only access token.
- `dcarbn_refresh`: rotating, HTTP-only refresh token scoped to authentication APIs.
- `dcarbn_csrf`: readable CSRF token submitted through `X-CSRF-Token`.

Production deployments must enable `COOKIE_SECURE=true`, use HTTPS, restrict
`COOKIE_DOMAIN`, and choose `strict` or `lax` SameSite behavior according to the
deployment topology. Bearer-token authentication remains available for
non-browser integration clients.

## Refresh-token rotation

Refresh tokens are opaque random values. Only their SHA-256 hashes are stored.
Each successful refresh revokes the old session and links it to its replacement.
Presenting a revoked token triggers reuse detection and revokes all sessions for
the user.

## MFA

TOTP enrollment encrypts the authenticator secret at rest using a key derived
from `MFA_ENCRYPTION_KEY`. Enrollment requires a valid six-digit code. The
platform generates ten single-use recovery codes and stores only their hashes.

Login with MFA has two stages:

1. Password and tenant verification.
2. A five-minute MFA challenge with a configurable attempt limit.

## Password recovery

Password-reset requests return the same response regardless of whether the
account exists. Valid requests create a single-use, time-limited token, send a
transactional email, and record a security event. Completing a reset increments
the user's token version and revokes all sessions.

## Email delivery

`EMAIL_PROVIDER=console` is suitable for local development. Production can use
the SMTP provider with TLS and authenticated credentials. Invitation and
password-reset messages are delivered through the provider abstraction.

## Security monitoring

Tenant administrators and auditors can query `/api/v1/security/events`.
Platform administrators can review events across tenants. Events include login
failures, account blocks, MFA challenges, refresh rotation, token reuse,
password recovery, role changes, invitations, and tenant onboarding.

Security events preserve severity, outcome, tenant, user, IP address, user
agent, correlation ID, structured metadata, and timestamp.
