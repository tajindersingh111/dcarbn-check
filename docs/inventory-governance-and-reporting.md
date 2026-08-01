# Inventory Governance and Audit-Ready Reporting

## Approval

An approval request is tied to one completed calculation run. The platform
evaluates four controls:

- Evidence completeness
- Approved organisational boundary
- Factor lineage completeness
- Calculation completeness

The requester cannot review their own approval request. Only the assigned
reviewer can approve or reject it.

## Locking

Only an approved inventory can be locked. Locking creates an immutable lock
record containing:

- Approval reference
- Calculation-run reference
- Inventory version
- Result count
- Lock reason
- Approval snapshot
- Actor and timestamp

A locked inventory cannot be edited or recalculated.

## Restatement

Approved or locked inventories are never overwritten. A restatement records:

- Reason
- Materiality assessment
- Requested changes
- Independent decision
- Replacement inventory reference

Approval creates a new draft inventory version and marks the original as
superseded. Completion requires the replacement inventory to be approved or
locked.

## Audit-ready reporting

Reports are immutable JSON snapshots with a canonical SHA-256 hash. They
contain:

- Inventory and reporting period
- Organisational boundary
- Approval metadata
- Calculation-run metadata
- Scope and category totals
- Factor-set references and source hashes
- Data-quality summary
- Activity-level results
- Warnings and intermediate lineage

Finalizing a newer report supersedes the previous final report without
deleting it.

## APIs

```text
POST /api/v1/inventories/{inventory_id}/approval-requests
GET  /api/v1/inventory-approvals/{approval_id}
POST /api/v1/inventory-approvals/{approval_id}/start-review
POST /api/v1/inventory-approvals/{approval_id}/decision

POST /api/v1/inventories/{inventory_id}/lock

POST /api/v1/inventories/{inventory_id}/restatements
GET  /api/v1/inventory-restatements/{restatement_id}
POST /api/v1/inventory-restatements/{restatement_id}/decision
POST /api/v1/inventory-restatements/{restatement_id}/complete

POST /api/v1/inventories/{inventory_id}/audit-reports
GET  /api/v1/audit-reports/{report_id}
```
