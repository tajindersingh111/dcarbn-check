# DATa Operational-Emissions Review and Conversion

## Purpose

Confirmed DATa operational-emissions results enter a controlled review
workflow before they become corporate inventory results.

DATa supplies the specialist transport result and lineage. The carbon
platform controls the reporting inventory, final scope/category, review,
conversion and audit history.

## Workflow

```text
confirmed DATa result
  → pending
  → in_review
  → approved
  → converted

confirmed DATa result
  → pending
  → in_review
  → rejected
```

## Preconditions

Conversion requires:

- An active tenant.
- A confirmed DATa classification.
- A selected editable inventory.
- A calculation date inside the inventory reporting period.
- A valid confirmed scope.
- A Scope 3 category when confirmed as Scope 3.
- Reviewer approval.
- No previous conversion for the same operational-emission record.

## Immutable conversion

Conversion creates:

1. A dedicated carbon activity sourced from DATa.
2. A completed calculation run.
3. A calculation result using `external_operational_result`.

The DATa total is copied directly into `gross_kg_co2e` and
`allocated_kg_co2e`. The platform does not apply another emission factor.

```text
allocated_kg_co2e =
    verified DATa operational result
```

The result preserves:

- External calculation ID
- DATa methodology version
- Source record version and hash
- Calculation timestamp
- CO2, CH4 and N2O components
- Journey, shipment and vehicle external IDs
- Data-quality level and score
- Complete DATa lineage metadata
- Reviewer and inventory snapshot

## Idempotency

One review is allowed per tenant and operational-emission record. Converted
reviews return their existing calculation references if conversion is
requested again.

## APIs

```text
POST /api/v1/integrations/data/reviews/sync
GET  /api/v1/integrations/data/reviews
GET  /api/v1/integrations/data/reviews/{review_id}

POST /api/v1/integrations/data/reviews/operational-emissions/{emission_id}
POST /api/v1/integrations/data/reviews/{review_id}/start
POST /api/v1/integrations/data/reviews/{review_id}/decision
POST /api/v1/integrations/data/reviews/{review_id}/convert
```

## Separation of responsibilities

The review snapshot records the confirmed classification and the target
inventory at review start. Later DATa source updates move the operational
record back to review-required status through the integration layer; they do
not modify the immutable converted result.
