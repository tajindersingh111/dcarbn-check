# Activity Data and Emissions Calculation Engine

## Activity model

Activities are tenant-scoped, inventory-linked, versioned records. The first
release supports:

- Mobile combustion
- Stationary combustion
- Refrigerants
- Purchased electricity
- Purchased heat, steam and cooling
- Freight transport
- Business travel
- Employee commuting

Each activity retains its original quantity and unit, normalized quantity,
scope classification, factor matching hierarchy, allocation percentage,
evidence reference, data-quality rating, source-system identifier, version,
and source metadata.

## Versioning

`source_system + source_record_id` identifies the source activity. Submitting
a newer version supersedes the previous current record; historical records
remain available.

## Calculation runs

A calculation run snapshots all current validated activities and creates one
immutable result per activity. Each result records:

- Selected factor and factor-resolution record
- Original and factor-compatible activity values
- Factor value
- Allocation percentage and multiplier
- Gross and allocated kgCO2e
- Formula and intermediate values
- Warnings
- Methodology version

## Formula

```text
gross_kg_co2e =
    factor_activity_value × factor_value

allocated_kg_co2e =
    gross_kg_co2e × (allocation_percentage ÷ 100)

t_co2e =
    kg_co2e ÷ 1,000
```

## Scope 2

Location-based and market-based activities are stored separately through the
`scope_2_method` field and remain separate in summaries.

## APIs

```text
POST  /api/v1/inventories/{inventory_id}/activities
GET   /api/v1/inventories/{inventory_id}/activities
GET   /api/v1/activities/{activity_id}
PATCH /api/v1/activities/{activity_id}

POST /api/v1/inventories/{inventory_id}/calculation-runs
GET  /api/v1/calculation-runs/{run_id}
GET  /api/v1/calculation-runs/{run_id}/results
GET  /api/v1/calculation-runs/{run_id}/summary
```

Failed factor resolutions cause the calculation run to fail visibly. The
engine does not silently substitute a weak proxy.
