# D-carbN local demonstration workspace

This is a standalone, database-free prototype for customer workshops. It reuses
the production platform's visual language and governed calculation concepts,
but it does not call the API, connect to PostgreSQL or change the production
application.

The demo follows the approved D-carbN Analytics visual reference: deep ink
navigation, carbon-green highlights, a clean white editorial canvas and locally
bundled Lato 400/700 fonts. Its visual identity does not depend on an internet
font service.

## Run locally

From the repository root:

```bash
python3 -m http.server 8081 --directory local-demo
```

Open <http://127.0.0.1:8081> in a modern browser.

All changes are stored in that browser's `localStorage`. Use **Export workspace
JSON** before clearing browser data if a workshop state must be retained. The
**Reset demo** control restores the original New Era Group sample inventory.
The default reporting period is **Calendar year 2025**.

## Demonstration workflow

The role selector demonstrates the intended commercial SaaS boundary. It is a
prototype aid, not local authentication.

1. As **New Era Contributor**, download the relevant template, upload and validate data,
   then submit the inventory to D-carbN. Calculation outputs and reports remain
   unavailable to this role before release.
2. As **D-carbN Analyst**, review methodology, factor selection, evidence and
   lineage; approve or return every submitted activity.
3. As **D-carbN Approver**, inspect the completed inventory and lock the final
   immutable report.
4. After release, the customer contributor can inspect the governed results and
   customer report.

The demo automatically advances between roles after each workflow hand-off so
the complete service model can be shown on one computer.

## Supported local data contract

The upload accepts CSV or JSON records with these fields:

| Field | Requirement |
|---|---|
| `source_record_id` | Required and unique in the workspace |
| `activity_date` | Required valid date |
| `description` | Required |
| `calculation_method_id` | Must match a supported governed method |
| `activity_value` | Required positive number |
| `activity_unit` | Must exactly match the method contract |
| `evidence_reference` | Required reference; evidence files are not embedded |
| `equipment_reference` | Required for R410A service top-ups |
| `supplier_name` | Required for supplier-specific results |
| `supplier_methodology` | Required for supplier-specific results |
| `supplier_methodology_version` | Required for supplier-specific results |
| `boundary_description` | Required for supplier-specific results |
| `assurance_status` | Required for supplier-specific results |

Excel workbooks should be saved as **CSV UTF-8** for this first local-demo
iteration. This deliberately keeps the prototype dependency-free and prevents
customer data being sent to a third-party conversion service.

## Template library

The Inventory Wizard includes a D-carbN CSV counterpart for every supplied
reference file, plus the employee-commuting requirement identified in the Word
questionnaire:

- Organisation information (FTE, headcount, revenue and reporting period)
- Utilities and rent
- Company vehicles and business travel
- Procurement
- Transportation and distribution
- Employee commuting

The **Download combined activity CSV** action combines the five activity packs;
organisation information remains a separate one-row CSV because it is validated
as reporting metadata rather than an emission activity. Each activity guide row
is pre-filled with its governed method ID, compatible unit and a plain-language
`row_purpose`. Customers complete the source ID, date, description, value and
evidence fields, remove unused guide rows and upload the saved CSV through the
same Inventory Wizard.

The activity CSVs retain source-workbook fields for site, transport type, fuel,
ownership, origin/destination, return journeys, passengers/rooms, journeys/nights,
distance, payload, spend, supplier-data status and notes. Where complete
components are supplied, the importer derives passenger-km, tonne-km or room
nights. If a manually entered total disagrees with those components, the row is
blocked. Accepted source fields are preserved in calculation lineage.

The guided Scope 1, Scope 2 and Scope 3 cards each generate a downloadable CSV
containing every governed method currently supported for that scope. This
catalogue-driven route ensures that a supported category cannot be omitted from
the downloadable template set.

## Validation and local-session controls

Validation messages identify the field to correct and explain the expected
format or value. Source IDs are compared case-insensitively against both the
existing local inventory and other rows in the same file. Activity dates must
fall inside the reporting period. Flagged rows remain outside the inventory and
the interface provides a correction checklist before re-upload.

**Export pilot session** downloads the complete browser session as JSON,
including activity data, calculations, evidence references, audit history and
any locked report identity. **Clear all local customer data** removes those
records from the active browser session after an explicit confirmation. The
normal **Reset demo** action remains available for restoring fictional data.

Spend-only estimates, water use, rent and other inputs without an approved
calculation route are not silently converted. They remain outside the governed
activity import until D-carbN defines and approves the required method.

## Important boundary

This workspace demonstrates intended operation and user experience. It is not a
substitute for the hosted platform's authentication, tenant isolation, database
controls, immutable audit storage, approvals or controlled migrations. Report
outputs are marked as prototypes and must not be represented as externally
assured filings.

The bundled factor mappings use the revised July 2026 DESNZ UK Government GHG
Conversion Factors. Unsupported combinations are flagged rather than assigned a
nearby factor.

The page Content Security Policy uses `connect-src 'none'`, and the JavaScript
contains no API, database or telemetry client. Customer uploads, calculations,
exports and reports therefore remain on the computer running the browser pilot.
