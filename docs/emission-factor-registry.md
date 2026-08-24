# UK Emission-Factor Registry

## Source workbook contract

The importer targets the official UK Government flat-format workbooks for the
supported reporting years (currently 2024 and 2026) and reads:

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
  - `GHG Conversion Factor <reporting year>`

The reporting year is explicit at the API and command boundary. The importer
rejects a workbook when the required worksheet or exact year-specific header
contract changes. This prevents silent column shifts and accidental use of a
factor pack for the wrong year.


## Blank factor cells

The official flat-format workbooks include catalogue combinations for which no
conversion factor is published. These rows retain identifiers and category
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

UK 2024 final v1.1:

```bash
python -m app.scripts.import_uk_2024_factors \
  /data/ghg-conversion-factors-2024-FlatFormat_v1_1.xlsx \
  --dataset-version 2024-v1.1 \
  --publication-date 2024-10-30 \
  --effective-from 2024-01-01 \
  --effective-to 2024-12-31
```

UK 2026:

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

`POST /api/v1/emission-factor-sets/import/uk-2024`

`POST /api/v1/emission-factor-sets/import/uk-2026`

Multipart fields:

- `workbook`: the `.xlsx` file
- `metadata_json`: JSON matching `FactorSetImportMetadata`

## Numerical handling

Factor values are parsed into Python `Decimal` and stored as
`NUMERIC(30, 15)`. The source text, source row number, and complete raw row
are retained for auditability.

## UK 2024 source controls

- Publication page: https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024
- Required workbook: final flat-format v1.1, updated 30 October 2024
- Expected SHA-256: `1b063892ad1f00c5bc73029c016e54bc4c3050a71219202b545f8aea2f9f75c4`
- Methodology paper: https://assets.publishing.service.gov.uk/media/66a9fe4ca3c2a28abb50da4a/2024-greenhouse-gas-conversion-factors-methodology.pdf

The source hash is retained on the factor set. Operators must independently
approve the imported draft before the calculation engine can resolve it.
