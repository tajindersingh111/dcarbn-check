# Unit Normalisation and Factor Resolution

## Principles

- All quantities are represented with `Decimal`.
- Original values and units are preserved.
- Units are resolved through a central registry.
- Cross-dimensional conversions are rejected.
- Approved factor sets are used by default.
- Previous-year and geography fallbacks require explicit flags.
- Equal top scores produce `ambiguous`, not an arbitrary selection.
- Persisted resolutions store criteria, candidates, warnings, score, and result.

## Canonical base units

| Dimension | Base unit |
|---|---|
| Mass | kg |
| Distance | km |
| Volume | litre |
| Energy | kWh |
| Currency | GBP |
| Vehicle distance | vehicle-km |
| Mass-distance | tonne-km |
| Passenger-distance | passenger-km |
| Time | hour |
| Count | unit |

## Resolution order

Candidate factors are restricted to approved factor sets and scored by:

1. Greenhouse-gas component
2. Explicit factor-set restriction
3. Scope
4. Reporting year
5. Geography
6. Unit compatibility
7. Level 1 through Level 4 category matches
8. Column-text match
9. Lifecycle boundary

A previous-year or geography fallback is marked with a warning and receives
`fallback` match strength.

## APIs

```text
POST /api/v1/units/normalize
POST /api/v1/emission-factors/resolve
GET  /api/v1/factor-resolution-records/{resolution_record_id}
```

## Example resolution request

```json
{
  "activity_value": "1250.50",
  "activity_unit": "litres",
  "reporting_year": 2026,
  "geography_code": "GB",
  "scope": "Scope 1",
  "level_1": "Fuels",
  "level_2": "Liquid fuels",
  "level_3": "Diesel",
  "lifecycle_boundary": "direct",
  "greenhouse_gas_component": "total_co2e",
  "allow_previous_year": false,
  "allow_geography_fallback": false,
  "persist": true
}
```

## Calculation

Once resolved:

```text
resulting kgCO2e =
    activity converted to the factor denominator unit
    × factor value
```

The full calculation engine will consume the persisted resolution rather
than searching for a factor again during report generation.
