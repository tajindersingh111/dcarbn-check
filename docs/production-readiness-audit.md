# Production-readiness audit

**Repository:** `Leonardfraser/Dcarbn-Scope-1-2`  
**Audit baseline:** main at `7648787`  
**Purpose:** distinguish staging readiness, production launch blockers and post-launch improvements.

## Executive conclusion

The platform has a strong engineering and control foundation: multi-tenant domain
models, governed emissions calculations, cookie authentication, MFA, CSRF controls,
rate limiting, immutable audit evidence, CI, supply-chain scanning, backups,
observability and recovery architecture are present.

It is suitable to proceed towards an isolated staging deployment after the
remediation in this pull request passes CI. It is not yet approved for production.
The remaining production gates require real infrastructure, named providers and
independent operational evidence; they cannot be proven from source code alone.

## Evidence reviewed

- FastAPI application routing, settings validation, authentication and security middleware
- Tenant membership, role and platform-administrator models
- Next.js authentication shell and primary workflow browser tests
- PostgreSQL, Redis, gateway, Caddy, production and IONOS staging Compose definitions
- Main CI, resilience validation and supply-chain security workflows
- Production-hardening, backup, recovery and IONOS operator documentation

## Readiness register

| Area | Status | Evidence or required action |
|---|---|---|
| Build and automated tests | Ready | Backend, frontend and Playwright suites run in CI. |
| Supply-chain controls | Ready for staging | Dependency, container, secret and licence controls are automated. |
| Staging deployment pack | Ready after this PR | Compose validation, TLS gateway, secret files, health checks and rollback are defined. |
| Authentication and sessions | Ready for staging | Argon2id, rotating cookie sessions, CSRF, MFA and recovery controls exist. |
| First administrator bootstrap | Remediated in this PR | One-time command creates the initial tenant/admin and refuses subsequent bootstrap. |
| Staging configuration safety | Remediated in this PR | Staging now receives the same fail-fast hardening checks as production. |
| Client address trust | Remediated in this PR | Identity and recovery events use trusted-proxy resolution rather than raw headers. |
| Role-aware interface | Remediated in this PR | Privileged links are hidden unless the current user has the corresponding role. |
| Environment identification | Remediated in this PR | Development, staging and production workspaces are labelled correctly. |
| Managed production identity | Production blocker | Select an identity provider and asymmetric-token approach, or formally accept self-hosted identity risk. |
| Live end-to-end validation | Staging gate | Current browser journeys use controlled API fixtures; execute them against the deployed stack and real database. |
| Backup restoration | Production blocker | Complete and retain evidence from an encrypted backup restore and recovery drill. |
| Monitoring and alerts | Production blocker | Connect real alert recipients, verify delivery and establish an on-call owner. |
| Performance and capacity | Production blocker | Run representative fleet/import/report workloads and agree thresholds. |
| Accessibility | Production blocker | Complete automated and manual WCAG 2.2 AA review of core journeys. |
| Penetration testing | Production blocker | Commission an independent authenticated and unauthenticated test after staging stabilises. |
| Privacy and retention | Production blocker | Approve data retention, deletion, privacy notice, processor list and incident process. |

## Core staging acceptance journeys

1. Bootstrap the initial platform administrator and sign in.
2. Enable MFA, sign out, sign in with MFA and verify a recovery code.
3. Onboard a tenant and accept the owner invitation.
4. Create users with contributor, reviewer, approver, auditor and administrator roles.
5. Verify each role can access only its intended screens and API actions.
6. Create an organisation, boundary, reporting period and inventory.
7. Import factors and activities; verify idempotency and row-level error handling.
8. Submit DATa operational results, review them and convert approved results.
9. Run calculations; verify Scope/category totals and factor lineage.
10. Submit, approve and lock an inventory; generate and re-open audit evidence.
11. Exercise password reset, account lockout, administrator unlock and session revocation.
12. Re-deploy, roll back application images, restore a database backup and retain evidence.

## Release decision

- **Proceed to staging:** yes, after this remediation PR is green and merged.
- **Proceed to stakeholder UAT:** only after the server, DNS, SMTP, secrets, bootstrap and live smoke tests are complete.
- **Proceed to production:** no, until every production blocker above has an owner, evidence and formal approval.
