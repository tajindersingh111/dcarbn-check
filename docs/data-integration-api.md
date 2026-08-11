# DATa Integration API

## Ownership

DATa owns operational vehicle, journey, route, fuel, payload and specialist
transport-calculation data.

The carbon platform owns tenant mapping, organisational boundaries, final
scope/category classification, inventory consolidation, approval and reporting.

DATa may suggest a scope and Scope 3 category. The carbon platform records that
suggestion separately from the confirmed classification.

## Authentication

Production clients should use OAuth2 client credentials and receive a short-lived
bearer token containing:

```json
{
  "sub": "data-service-client",
  "tenant_id": "tenant-uuid",
  "roles": ["integration_client"],
  "aud": "dcarbn-carbon-platform"
}
```

## Import order

Recommended order:

1. Organisation mapping
2. Vehicles
3. Shipments
4. Journeys
5. Fuel records
6. Payload records
7. Operational-emission calculations

Referenced external records must already exist. Missing references produce
row-level errors rather than corrupting relationships.

## Endpoints

```text
POST /api/v1/integrations/data/organisation-mappings
POST /api/v1/integrations/data/vehicles/batch
POST /api/v1/integrations/data/shipments/batch
POST /api/v1/integrations/data/journeys/batch
POST /api/v1/integrations/data/fuel/batch
POST /api/v1/integrations/data/payloads/batch
POST /api/v1/integrations/data/operational-emissions/batch

GET  /api/v1/integrations/data/imports/{batch_id}
GET  /api/v1/integrations/data/imports/{batch_id}/errors
POST /api/v1/integrations/data/operational-emissions/{id}/classification
GET  /api/v1/integrations/data/reconciliation
```

## Idempotency

Every batch requires an `idempotency_key`.

- Replaying the same key and identical payload returns `duplicate`.
- Reusing the key with a different payload returns HTTP 409.
- Individual records are upserted by tenant plus stable external ID.
- Source hashes prevent unnecessary updates.

## Operational-emissions payload

```json
{
  "schema_version": "1.0",
  "idempotency_key": "data-emissions-2026-08-01-001",
  "records": [
    {
      "external_customer_id": "customer-1042",
      "external_calculation_id": "data-calc-2026-000184",
      "external_journey_id": "JRN-55420",
      "external_shipment_id": "SHP-77831",
      "external_vehicle_id": "VEH-209",
      "suggested_scope": "scope_3",
      "suggested_scope_3_category": 4,
      "classification_reason": "Purchased third-party freight service",
      "methodology_version": "DATa-2026.1",
      "total_kg_co2e": "326.745",
      "co2_kg": "318.220",
      "ch4_kg_co2e": "2.115",
      "n2o_kg_co2e": "6.410",
      "data_quality_level": "primary",
      "data_quality_score": 92,
      "calculated_at": "2026-08-01T10:15:00Z",
      "source_record_version": "3",
      "source_hash": "sha256-compatible-source-hash",
      "lineage": {
        "distance_source": "telematics",
        "fuel_source": "fuel_card",
        "payload_source": "shipment_record"
      }
    }
  ]
}
```

## Classification

DATa operational results are not silently assigned to the corporate inventory.
A reviewer confirms the scope/category and may link the result to an existing
carbon activity. This prevents DATa's suggested classification from overriding
the reporting company's boundary configuration.

## Reconciliation

The reconciliation endpoint reports imported record counts, unclassified
operational-emission records and activity links for the authenticated tenant.


## Accounting and CSV Scope 3 supplier results

The accounting contract accepts supplier/investee-specific reported emissions for
Categories 1, 2, 8 and 10-15 from CSV, QuickBooks, Xero, Sage or a direct API.
It does not infer emissions from spend or silently treat a ledger account as a
Scope 3 classification.

```text
GET  /api/v1/integrations/data/accounting/scope-3/template
POST /api/v1/integrations/data/accounting/scope-3/batch
```

The template endpoint returns the supported sources, exact required and optional
columns, and the governed method identifier for every supported category. The
customer CSV template is available at
`docs/templates/scope3-accounting-supplier-results.csv`.

Each import preserves two distinct evidence layers:

- the accounting transaction: source system, transaction ID, account, date,
  currency, amount and source document;
- the emissions assertion: supplier/investee, methodology and version,
  reporting period, lifecycle boundary, assurance status and evidence reference.

The platform calculates only the declared allocation:

```text
allocated kgCO2e = supplier-reported kgCO2e × allocation percentage ÷ 100
```

The resulting record enters the existing operational-emissions review queue.
The suggested Scope 3 category never overrides the customer's approved
classification or inventory boundary.

Categories 3-7 and 9 continue to use their governed activity-data routes where
published factors or transport-specific methods apply. They are deliberately
rejected by this supplier-result accounting contract.


## Accounting synchronisation pagination

`GET /api/v1/integrations/data/accounting/syncs` is a cursor-paginated tenant history. It accepts:

- `connection_id` to narrow the history to one tenant-owned connection;
- `limit` from 1 to 100, default 50;
- opaque `cursor` returned by the preceding page.

The response contains `items` and `next_cursor`. Ordering is newest first using
`created_at` and the unique record ID. A cursor is cryptographically bound to
the authenticated tenant; modified or cross-tenant cursors are rejected with
HTTP 422. Clients must not decode the token or derive tenant context from it.

Accounting connection registers and import-error reads retain their existing
array response for compatibility, with a server-enforced maximum of 100 records.
