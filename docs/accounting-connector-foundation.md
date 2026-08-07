# Accounting connector foundation

This tranche establishes the platform-side security and identity contract for
QuickBooks, Xero, Sage, CSV and direct API sources. It builds on the governed
Scope 3 accounting contract and customer wizard delivered in PRs #38 and #39.

## What the foundation governs

Each provider declares:

- authentication mode;
- incremental-sync support;
- webhook support;
- whether an external company identity is mandatory.

Mapping profiles are versioned and must map every governed target exactly once.
A source field cannot silently feed two emissions fields.

Every synchronisation request is bound to:

- tenant;
- customer;
- provider;
- external accounting company;
- mapping-profile version;
- cursor;
- requested reporting window.

Those fields produce a deterministic SHA-256 sync identity. Retrying the same
cursor and reporting window therefore produces the same identity, while the next
cursor produces a different identity.

## Credential boundary

The application must never request or store a customer's accounting password.

OAuth access and refresh tokens, API keys and client secrets belong only in the
production secret provider. They must not appear in database diagnostics, API
responses, application logs, exception messages or audit-event metadata. The
connector foundation supplies recursive redaction for those surfaces.

## Connection lifecycle

The governed lifecycle is:

1. draft;
2. authorizing;
3. active;
4. action required; or
5. revoked.

A connection can become active only after tenant ownership, external-company
identity and provider authorization have been confirmed. Revocation must stop
new sync jobs without deleting historical import lineage.

## Import boundary

A successful connector sync does not add emissions directly to an inventory.
Source records continue through:

1. governed mapping;
2. row validation;
3. idempotent batch import;
4. customer classification review;
5. evidence review; and
6. inventory approval.

This preserves the existing rule that accounting data may support a Scope 3
result but cannot silently infer emissions from spend or approve a category.

## Next implementation increment

The next increment adds persistent tenant-scoped connection and sync-job models,
a database migration, role-controlled API routes and audit events. Live OAuth
activation will then be implemented against vendor sandbox accounts and approved
callback URLs.
