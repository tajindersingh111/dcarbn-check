# Staging user-acceptance test plan

## Purpose

Prove that D-carbN's core workflows, permissions, audit evidence and recovery controls work in the deployed staging environment. This is a business acceptance exercise, not a substitute for penetration, accessibility or load testing.

## Entry criteria

- PR and main-branch checks are green.
- Staging URL uses valid HTTPS and displays **Staging workspace**.
- PostgreSQL and Redis are healthy; migrations are current.
- SMTP test delivery works.
- The initial platform administrator has been bootstrapped.
- Synthetic fixtures under `docs/uat/fixtures/` are approved for use.
- Testers have named roles and must not share accounts.

## Roles

| Tester | Platform role | Primary responsibility |
|---|---|---|
| Platform operator | Platform administrator | Bootstrap, tenant onboarding and operational checks |
| Tenant owner | Tenant administrator | Users, roles and tenant governance |
| Data preparer | Data contributor | Organisation and activity entry |
| Sustainability lead | Sustainability manager | Inventory, factor and calculation workflows |
| DATa reviewer | Data reviewer | Operational-emissions classification |
| Approver | Inventory approver | Independent approval and locking |
| Auditor | Auditor | Evidence and read-only assurance |

Use staging-only addresses at a controlled domain. Passwords and MFA recovery codes must never be entered in this document.

## Evidence standard

For every test, record tester, UTC time, result, screenshot or export reference, relevant record ID and defect link. A test passes only when the expected result and its negative permission check both succeed.

## Test cases

| ID | Journey | Role | Expected result |
|---|---|---|---|
| UAT-001 | Bootstrap the initial administrator once | Operator | Initial tenant/admin created; a second bootstrap attempt is refused |
| UAT-002 | Sign in, sign out and refresh session | Operator | Secure cookie session works; sign-out invalidates access |
| UAT-003 | Enable MFA and use a recovery code once | Operator | MFA succeeds; the used recovery code cannot be reused |
| UAT-004 | Request and complete password reset | Tenant owner | Non-enumerating response; prior sessions are revoked |
| UAT-005 | Onboard the synthetic tenant | Operator | Tenant and owner invitation created; non-platform user is denied |
| UAT-006 | Accept invitation | Tenant owner | Account activates and opens the correct tenant workspace |
| UAT-007 | Invite all workflow roles | Tenant owner | Each invitation has only the intended role |
| UAT-008 | Verify role-aware navigation | Every role | Privileged links are absent where unauthorised |
| UAT-009 | Attempt unauthorised API mutations | Auditor/contributor | API returns 403 and no record changes |
| UAT-010 | Create and update organisation | Contributor | GB is normalised; tenant ownership is retained |
| UAT-011 | Confirm cross-tenant isolation | Tenant owner | IDs from another tenant return no accessible data |
| UAT-012 | Create reporting boundary and inventory | Sustainability lead | Effective dates and consolidation method persist |
| UAT-013 | Import/approve an emission-factor set | Sustainability lead | Version, source hash and approval state are retained |
| UAT-014 | Submit Scope 1 activity | Contributor | Activity validates and preserves source/evidence lineage |
| UAT-015 | Submit Scope 2 activity | Contributor | Location/market method is required and retained |
| UAT-016 | Submit Scope 3 category 4 activity | Contributor | Category validation succeeds; missing category is rejected |
| UAT-017 | Re-submit a source record | Contributor | Idempotency/version behaviour matches the documented contract |
| UAT-018 | Import vehicle/journey/fuel batches | Integration user | Counts reconcile; duplicate idempotency key is safe |
| UAT-019 | Import an invalid journey | Integration user | Row-level error identifies missing distance unit |
| UAT-020 | Review DATa operational emissions | DATa reviewer | Suggested classification can be confirmed or rejected with audit event |
| UAT-021 | Run calculations | Sustainability lead | Decimal totals, factor resolution and warnings are reproducible |
| UAT-022 | Submit inventory for approval | Sustainability lead | Workflow state changes and editing rules apply |
| UAT-023 | Approve and lock inventory | Approver | Independent approval locks the inventory |
| UAT-024 | Produce audit report | Auditor | Report hash and underlying immutable payload can be reopened |
| UAT-025 | Change a user's role | Tenant owner | Existing sessions are revoked and new permission applies |
| UAT-026 | Trigger account lockout and unlock | Tenant owner | Threshold locks account; authorised unlock is audited |
| UAT-027 | Verify readiness and operational health | Operator | Dependencies, backup age and evidence state are visible |
| UAT-028 | Deploy the same release again | Operator | Deployment is repeatable without duplicate data or downtime defect |
| UAT-029 | Roll back application images | Operator | Previous application version returns healthy; database remains consistent |
| UAT-030 | Restore a backup to isolation | Operator/auditor | Restore completes and sampled records reconcile |

## Exit criteria

- All critical and high-priority tests pass.
- No unresolved severity-1 or severity-2 defects.
- Role and cross-tenant isolation tests pass without exception.
- Calculation totals and audit hashes are reproducible.
- Backup restore and application rollback evidence are retained.
- Product owner, technical owner and security owner sign the decision record.

## Defect severity

| Severity | Definition | Release rule |
|---|---|---|
| 1 Critical | Data exposure, tenant crossover, authentication bypass, corrupt calculation or unrecoverable loss | Stop testing and block release |
| 2 High | Core journey unavailable, incorrect approval/locking, failed backup/rollback | Block UAT exit |
| 3 Medium | Workaround exists; material usability or reporting defect | Named owner and target date required |
| 4 Low | Cosmetic or minor documentation issue | May enter backlog |
