# UK 2026 Emission-Factor Registry

## Source workbook contract

The importer targets the official flat-format workbook and reads:

- Worksheet: `Factors by Category`
- Header row: `6`
- Required columns:
  - ID
  - Scope
  - Level 1
  - Level 2
  - Level 3
  - Level 4
  - Column Text
  - UOM
  - GHG/Unit
  - GHG Conversion Factor 2026

The importer rejects a workbook when the required worksheet or exact header
contract changes. This prevents silent column shifts.


## Blank factor cells

The official flat-format workbook includes catalogue combinations for which no
2026 conversion factor is published. These rows retain identifiers and category
metadata but have a blank factor cell. The importer records them as skipped
unavailable rows. It does not import a null or zero factor, and it does not treat
them as malformed data.

## Versioning

Every import creates an immutable draft factor set identified by:

- Publisher
- Dataset name
- Dataset version
- Reporting year
- SHA-256 hash of the source workbook

Re-importing the same workbook and version creates a duplicate import job
linked to the existing factor set rather than copying factors.

Approved factor sets are never overwritten. A later approved set supersedes
an earlier set through an explicit relationship.

## Approval

Imported factor sets remain `draft` until a factor manager approves them.
Search endpoints return approved factors by default.

## Import command

```bash
python -m app.scripts.import_uk_2026_factors \
  /data/ghg-conversion-factors-2026-flat-format-revised.xlsx \
  --dataset-version 2026-revised \
  --reporting-year 2026 \
  --publication-date 2026-06-11 \
  --effective-from 2026-01-01 \
  --effective-to 2026-12-31
```

## API import

`POST /api/v1/emission-factor-sets/import/uk-2026`

Multipart fields:

- `workbook`: the `.xlsx` file
- `metadata_json`: JSON matching `FactorSetImportMetadata`

## Numerical handling

Factor values are parsed into Python `Decimal` and stored as
`NUMERIC(30, 15)`. The source text, source row number, and complete raw row
are retained for auditability.
