# Product requirements document (PRD)

## Purpose

D-carbN is a multi-tenant SaaS platform for governed Scope 1, Scope 2 and Scope 3 greenhouse-gas accounting. It converts operational, fleet, freight, accounting and customer-entered data into evidence-backed inventories and audit-ready reports without silently inferring or approving emissions.

## Users and outcomes

| User | Primary outcome |
|---|---|
| Customer contributor | Enter/import activity data with evidence and correct errors |
| Customer reviewer | Classify records, resolve exceptions and confirm completeness |
| Approver | Approve and lock a governed inventory |
| Auditor | Trace source, factor, methodology, calculation and change history |
| Tenant administrator | Manage users, roles, organisations and security |
| Methodology manager | Govern factors, methods and version changes |
| Platform operator | Monitor health, backup, recovery and security events |

## Functional requirements

### Identity and tenancy
- Users authenticate securely and operate only within authorised tenants.
- Invitations, password recovery, MFA, rotating sessions, lockout and role-based access are supported.
- Platform, tenant, methodology, auditor and contributor responsibilities remain separated.

### Organisational and reporting setup
- Customers maintain organisations, legal entities, sites, boundaries and reporting periods.
- Operational-control, financial-control and equity-share methods are versioned.
- Base year, significance thresholds, recalculation triggers and restatements are recorded.

### Data capture and integration
- Manual activity entry and governed CSV imports are supported.
- DATa imports support vehicle, shipment, journey, fuel, payload and operational-emission records.
- Connected-system foundations support QuickBooks, Xero, Sage and direct API sources.
- Imports are tenant-scoped, versioned, idempotent and reconciled as received/imported/rejected.
- Credentials are referenced from an approved secret store, never entered as raw passwords or tokens.

### Calculation and methodology
- Calculations use approved, effective-dated factors and Decimal-preserved values.
- Scope 1, Scope 2 and all 15 Scope 3 categories have governed calculation/evidence routes.
- Results preserve activity, unit-normalisation, factor, methodology and calculation lineage.
- Where no universal factor exists, supplier/investee or other evidence-backed methods are explicitly identified and approved.

### Review, approval and reporting
- Suggested classifications never become approved inventory data without review.
- Review queues expose errors, missing evidence and conflicts.
- Inventory approval applies control checks and creates an immutable lock.
- Restatements supersede rather than overwrite prior approved results.
- Reports show kgCO2e/tCO2e summaries, comparisons, methodology, warnings, evidence and hash-stamped lineage.
- PDF and CSV exports are supported.

## Non-functional requirements

- Tenant isolation on every customer-owned query and mutation.
- WCAG 2.2 AA target for customer journeys.
- Responsive support for current desktop/tablet/mobile browsers.
- Structured logging, metrics, traces, alerting and auditable security events.
- Encrypted backup, recovery testing, defined RPO/RTO and documented incident response.
- CI, dependency/secret/vulnerability scanning, SBOM, signed images and provenance.
- UK GDPR-aligned data minimisation, retention, access and deletion procedures.

## Acceptance and success

Launch acceptance requires: zero unresolved severity-1/2 defects; all required CI/security gates green; Paul’s business acceptance; a completed pilot; independent penetration testing; production hosting and secret storage; verified backup restoration; documented support ownership; and approved legal/commercial terms.

Initial product measures: time to first inventory, import success rate, exception rate, inventory approval time, report completion rate, pilot activation, renewal intent and support demand.
