# Identity, Access and Tenant Onboarding

## Authentication

The platform uses:

- Argon2id password hashing
- Short-lived signed access tokens
- Opaque rotating refresh tokens stored only as SHA-256 hashes
- Refresh-session revocation and replacement lineage
- User token versions for immediate role and account invalidation
- Active tenant, user and membership validation
- Tenant-scoped role claims
- Audited login-sensitive administration actions

Access tokens are intended for API authorization. Refresh tokens should be
moved to secure, HTTP-only, same-site cookies before public internet
deployment. The current browser storage implementation provides a complete
application flow but remains a deployment hardening item.

## Built-in roles

- `tenant_admin`
- `sustainability_manager`
- `data_contributor`
- `data_reviewer`
- `inventory_approver`
- `integration_client`
- `auditor`

Custom tenant roles can be created, while built-in system roles remain
identifiable and governed.

## Tenant onboarding

Platform administrators create a tenant workspace and owner invitation.
Onboarding automatically provisions the built-in role catalogue and assigns
the owner invitation the `tenant_admin` role.

## Main APIs

```text
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
GET  /api/v1/auth/me
POST /api/v1/auth/invitations/accept
POST /api/v1/auth/change-password

GET  /api/v1/users
POST /api/v1/users/invitations
PATCH /api/v1/users/{membership_id}/roles
PATCH /api/v1/users/{membership_id}/status

GET  /api/v1/roles
POST /api/v1/roles

POST /api/v1/platform/tenants/onboard
```
