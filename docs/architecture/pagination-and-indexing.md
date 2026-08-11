# Pagination and query-index contract

Status: implementation baseline for issue #50  
Owner: platform engineering  
Review trigger: any new collection endpoint, filter, sort order or table expected to exceed 10,000 rows per tenant

## Objectives

The API must not load or return an unbounded customer collection. High-volume histories use deterministic keyset pagination; compatibility endpoints retain bounded offset pagination until their clients are migrated.

## Contract

### Opaque cursor collections

Accounting synchronisation history and durable workloads use an opaque, HMAC-SHA256 cursor.

- The cursor position is `(created_at, id)`.
- Results are ordered by `created_at DESC, id DESC`.
- The unique `id` tie-breaker prevents duplicate or missing records when timestamps are equal.
- The authenticated tenant is included only in the server-side signature input. Tenant identity is not read from the cursor payload.
- Invalid, modified and cross-tenant cursors return HTTP 422.
- Default page size is 50; maximum page size is 100.
- Responses contain `items` and optional `next_cursor`; expensive total counts are omitted.
- Clients must treat cursors as opaque and must not persist them beyond the active browsing session.

Example response:

```json
{
  "items": [],
  "next_cursor": null
}
```

### Bounded compatibility collections

Existing activity, review, factor and workflow screens currently retain offset pagination with a server maximum of 200. Calculation-result reads are now bounded to 100 by default and 500 maximum while preserving an exact total count. Accounting connections and import-error responses are capped at 100.

A later client migration may move the remaining high-volume offset collections to the shared cursor contract. No endpoint may remove its server-side maximum.

## Endpoint inventory

| Collection | Expected volume | Access pattern | Current control |
| --- | ---: | --- | --- |
| Accounting synchronisation history | High | Tenant/connection, newest first | Opaque cursor, max 100 |
| Durable workloads | High | Tenant, status/type, newest first | Opaque cursor, max 100 |
| Calculation results | High | Tenant/run, chronological | Bounded offset, max 500 |
| Activities | High | Tenant/inventory filters | Bounded offset, max 200 |
| Data-review queue | High | Tenant/status | Bounded offset, max 200 |
| Emission factors | High but largely immutable | Narrow search/filter | Bounded offset, max 200 |
| Import errors | Medium/high per failed batch | Batch scoped | Bounded response, max 100 |
| Accounting connections | Low/medium | Tenant, newest first | Bounded response, max 100 |
| Users, organisations, inventories, approvals and reports | Low/medium | Tenant-scoped registers | Bounded offset, max 200 |
| Boundaries, reporting periods, factor sets and methodologies | Governance-limited | Tenant/platform register | Low-cardinality contract; review if cardinality policy changes |
| Scope 3 category dispositions | Fixed | 15 governed categories | Structurally bounded |

## Query-aligned indexes

Migration `0021` adds composite indexes matching tenant filters and deterministic ordering for:

- accounting connections;
- accounting sync history, with and without connection filtering;
- import errors;
- calculation results by tenant and run;
- durable workloads, including status and workload-type filters.

The controlled migration job must apply `0021` before deploying application code that relies on the new query paths. Because the production pilot has not started, the initial indexes are created in the normal migration transaction. Once live table sizes make lock duration material, index additions must use a separately reviewed PostgreSQL concurrent-index procedure.

## Performance targets

Representative staging data must meet these initial capacity targets:

- page size: 50 records, with 100 exercised as the upper cursor-page bound;
- API p95: at most 300 ms for cursor collections at 1,000,000 tenant rows;
- database execution p95: at most 100 ms for indexed page queries;
- no sequential scan on the high-volume relation for tenant-scoped cursor queries;
- returned rows: at most `limit + 1` at the database boundary;
- duplicate or missing IDs across equal-timestamp pages: zero.

Issue #53 owns the measured capacity evidence. These values are targets until that representative load run is completed.

## Rollout and compatibility

1. Apply migration `0021` through the controlled migration job.
2. Deploy the API and frontend together.
3. Confirm accounting history and workload endpoints return `items` plus `next_cursor`.
4. Confirm malformed and cross-tenant cursors return 422 without leaking tenant information.
5. Monitor API latency, database time and invalid-cursor rates.
6. Roll back application code before rolling back indexes; indexes are safe to leave in place during an application rollback.
7. Announce any future removal of offset compatibility in the API change log before changing clients.
