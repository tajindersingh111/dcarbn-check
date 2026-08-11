# PostgreSQL tenant-isolation contract

Status: implementation baseline for issue #51  
Owner: platform engineering and security  
Review trigger: every new table, authentication bootstrap path, worker type or operational database role

## Security outcome

Normal API and worker transactions run under PostgreSQL roles without BYPASSRLS. Tenant-owned tables have row-level security enabled and forced. The active tenant is stored with PostgreSQL set_config using transaction-local scope, so a pooled connection cannot carry context into its next transaction. Missing context returns no tenant rows and rejects tenant-owned writes.

Tenant identity comes from verified JWT claims or from the narrow security-definer resolver for one hashed opaque authentication token. Request payload identifiers never establish database context.

## Data catalogue

Tenant-owned tables include activity, boundary, calculation, data integration, review, factor-resolution, identity membership, reporting, inventory governance, organisation, security and durable-workload records. The migration keeps this explicit list reviewable.

Indirect tenant tables are protected through their parent relationships:

- data_import_errors through data_import_batches;
- membership_roles through both tenant_memberships and roles.

Methodology packs use a mixed policy: platform packs with no owner tenant are readable by all tenants but cannot be changed by a tenant transaction; tenant-owned packs are visible and writable only to their owner.

Platform-global tables are tenants, users, emission_factor_sets, emission_factors, factor_import_jobs, factor_import_errors and methodology_versions. Access to these tables remains governed by application roles and service-level authorisation. New tables must be classified before their migration is approved.

## Database roles

- dcarbn_app: normal API traffic, NOLOGIN and NOBYPASSRLS.
- dcarbn_worker: allowlisted background processing, NOLOGIN and NOBYPASSRLS. Its grants are limited to workload, calculation, inventory and audit records plus read-only governed factors and methodologies; it has no user, membership, session or credential-table access.
- migration owner: separate deployment credential that owns schema changes. It is never mounted into API or worker containers.
- break-glass operator: temporary, individually authenticated operational access. It is not created by application migrations and must be time-limited, ticketed and audited.

Migration 0022 grants the two restricted roles to the migration owner so the application can enter dcarbn_app with SET LOCAL ROLE. Production credentials must not be shared between application and migration jobs.

## Authentication bootstrap

Opaque refresh, MFA, invitation and password-reset tokens cannot reveal their tenant in application code. Function dcarbn_resolve_auth_tenant accepts only a fixed purpose and a token hash, returns only the matching tenant UUID, has a fixed search path and is executable only by dcarbn_app. It does not return customer data.

Login first resolves a platform-global tenant slug and then binds the verified tenant before reading memberships or writing tenant security events.

## Workers

A worker must choose a tenant from its approved rollout allowlist, start a new transaction, enter dcarbn_worker and set the tenant context before claiming or executing work. It must finish or roll back that transaction before selecting another tenant. A worker must never scan every tenant under an unrestricted role.

## Rollout

1. Back up and verify recovery evidence.
2. Apply migration 0022 with the controlled migration job.
3. Confirm the application login role can SET ROLE dcarbn_app but has no BYPASSRLS.
4. Deploy API and worker code together.
5. Run adversarial tenant tests in staging.
6. Verify unauthenticated, expired-token and cross-tenant identifiers return non-disclosing responses.
7. Confirm pool-reuse tests expose zero records without new tenant context.
8. Monitor database policy errors, authentication failures and workload retries.
9. Enable one approved pilot tenant only after evidence is signed off.

Rollback is application-first. Stop API and workers, restore the prior application release, then downgrade 0022 only through the migration job. Never disable RLS on a live application connection.

## Penetration and recovery scope

Independent testing must attempt cross-tenant select, update, delete, calculation, export and worker execution; opaque-token bootstrap misuse; SQL injection into role or tenant context; pool reuse; stale retries; methodology-pack mutation; and privilege escalation to migration or break-glass roles.

Recovery testing must confirm restored databases retain FORCE ROW LEVEL SECURITY, policies, function ownership and grants.
