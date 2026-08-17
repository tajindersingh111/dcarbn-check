# New Era Group browser-pilot readiness review

**Review date:** 17 August 2026
**Reviewed branch:** `agent/new-era-browser-pilot`
**Review basis:** browser-only local pilot at `http://127.0.0.1:8081/`
**Decision status:** approval required before any real New Era operational data is introduced

## Executive decision

The pilot is suitable for a fictional or irreversibly anonymised demonstration. It is **not ready for real New Era operational data**.

The tested upload, validation, calculation, evidence-reference, audit, export and locked-report journey works for the supplied fictional Scope 1, Scope 2 and Scope 3 files. However, five High risks remain: reporting-year/factor-year alignment, incomplete-file submission, non-restorable session exports, report locking without organisation metadata, and the intentional absence of controls appropriate to confidential customer data.

No subjective interface recommendation in this document has been implemented. Each is recorded for Leonard's approval.

## Review scope and evidence

The review used only repository-supplied fictional files:

- `sample/fictional-scope-1-2025.csv`
- `sample/fictional-scope-2-2025.csv`
- `sample/fictional-scope-3-2025.csv`
- `sample/new-era-group-activity-data.csv`
- `sample/new-era-group-activity-data.json`

Temporary invalid-date and session-export fixtures were created under `/private/tmp` for reproduction and deleted immediately after testing. They are not part of the repository.

Verified successful calculations:

| Fictional activity | Scope | Activity | Factor | Result |
|---|---:|---:|---:|---:|
| Head-office natural gas | 1 | 10,000 kWh Gross CV | 0.18231 | 1,823.10 kgCO2e |
| Purchased electricity | 2 | 50,000 kWh | 0.13096 | 6,548.00 kgCO2e |
| National rail travel | 3 | 1,000 passenger.km | 0.03092 | 30.92 kgCO2e |

## Issue summary

| Severity | Count | Pilot consequence |
|---|---:|---|
| Critical | 0 | No immediately exploitable or destructive Critical defect was found in the fictional local pilot. |
| High | 5 | Blocks use of real New Era operational data. |
| Medium | 4 | Requires a decision or remediation before a controlled customer pilot. |
| Low | 3 | Demonstration clarity and reuse improvements. |

## Detailed findings

### H1 — Calendar year 2025 is calculated with 2026 factor mappings

**Severity:** High
**Type:** calculation governance

**Reproduction**

1. Start a clean pilot session and confirm the reporting period reads `Calendar year 2025`.
2. Upload any supplied fictional Scope file.
3. Open Results or the locked report methodology section.
4. Observe calculation method IDs ending in `uk_2026.v1` and factor source `DESNZ UK Government GHG Conversion Factors 2026, revised July 2026`.

**Expected:** The reporting-year policy explicitly selects and discloses the factor set approved for Calendar year 2025, or explains and approves a different factor-year policy.
**Actual:** 2025 activity dates are calculated with the fixed 2026 factor catalogue.

**Recommendation for approval:** Do not change factors during this review. Leonard should approve either a 2025 governed factor catalogue or a documented policy authorising the 2026 factor set for this pilot, followed by calculation regression testing.

### H2 — Flagged rows do not block file acceptance or submission

**Severity:** High
**Type:** completeness and audit control

**Reproduction**

1. Open Inventory wizard in a clean contributor session.
2. Select **Load sample upload**.
3. Observe `2 valid · 1 flagged` and visible correction guidance.
4. Observe **Add valid rows to inventory** remains enabled.
5. Without correcting the flagged row, select **Submit to D-carbN**.
6. Observe the pilot advances to analyst review.

**Expected:** A flagged row remains an open control and blocks batch completion or submission until corrected or explicitly dispositioned with an audit reason.
**Actual:** Valid rows can proceed while the flagged row remains only in the temporary preview; submission checks the accepted inventory, not the unresolved preview.

**Recommendation for approval:** Choose one policy: reject the whole file, retain rejected rows as open controls, or require an explicit reviewer disposition. Recommended wording: “This file contains flagged rows. Correct or formally exclude every flagged row before submission.”

### H3 — Exported pilot sessions cannot be restored

**Severity:** High
**Type:** recoverability

**Reproduction**

1. Select **Export pilot session**.
2. Clear the local session or open a clean browser origin.
3. Attempt to upload the exported `new-era-group-2025-pilot-session.json` through Inventory wizard.
4. Select **Validate selected file**.
5. Observe `No activity rows were found.`

**Expected:** A control described as a complete session export has a documented, tested restore route that preserves activities, audit events, approvals and report identity.
**Actual:** The upload parser accepts an array or `{ records: [...] }`; the session export uses `{ session: {...} }` and cannot be restored.

**Recommendation for approval:** Add a separate **Restore pilot session** journey with format/version validation, explicit overwrite confirmation and hash checking. Until approved, change wording from “session export” to “diagnostic archive — not restorable.”

### H4 — A report can be locked without completed organisation metadata

**Severity:** High
**Type:** report completeness

**Reproduction**

1. Start a clean session; do not upload Organisation information.
2. Submit the seeded fictional activities.
3. Approve all ready records and complete analyst review.
4. Lock and release the report.
5. Observe `Locked customer release` and a SHA-256 identity.
6. Inspect readiness checks; no organisation-profile control is present.

**Expected:** Report locking requires approved organisational boundary, reporting dates, preparer and supporting reference.
**Actual:** `reportChecks()` tests activity, validation, review, evidence and method lineage only; empty profile fields do not block locking.

**Recommendation for approval:** Add an organisation-boundary readiness control and prevent final locking until its required fields are complete and reviewed.

### H5 — The browser-only storage model is not approved for confidential customer data

**Severity:** High
**Type:** privacy and operating model

**Reproduction**

1. Upload fictional data and reload the browser.
2. Observe that the session is recovered from browser `localStorage` without authentication.
3. Review `README.md` and `app.js`; the pilot deliberately has no hosted authentication, tenant isolation, encrypted database, server audit store or managed retention controls.

**Expected:** Real customer data is processed under an approved classification, access, encryption, retention, deletion, backup and incident-response model.
**Actual:** Data is browser-local and persistent on the computer profile. This is appropriate for a design prototype, not automatically for confidential operational data.

**Recommendation for approval:** Permit only fictional or irreversibly anonymised data until Leonard approves a written local-pilot data-handling protocol and New Era provides informed consent. Do not include personal data, employee-level travel, invoices or supplier-confidential attachments.

### M1 — Impossible calendar dates can pass validation

**Severity:** Medium
**Type:** data integrity

**Reproduction**

1. Create a valid activity row with `activity_date` set to `2025-02-30`.
2. Upload and validate it.
3. Observe `1 valid · 0 flagged` and an enabled **Add valid rows to inventory** button.

**Expected:** The date is rejected because 30 February does not exist.
**Actual:** Format and `Date.parse` checks accept the normalised date.

**Recommendation for approval:** Validate year, month and day by round-tripping the parsed components. Suggested message: “Enter a real calendar date in YYYY-MM-DD format.”

### M2 — Clear Local Data does not remove downloaded exports

**Severity:** Medium
**Type:** deletion expectations

**Reproduction**

1. Export a session or calculation CSV.
2. Select **Clear all local customer data** and confirm.
3. Observe the active browser session resets, while previously downloaded files remain in the computer's Downloads location.

**Expected:** The interface precisely states the deletion boundary.
**Actual:** Browser storage is reset, but local files outside browser storage cannot be removed by the application.

**Recommendation for approval:** Change wording to “Clear browser-stored pilot data” and add: “Downloaded CSV, JSON and printed files must be deleted separately.”

### M3 — The report-hash fallback is not SHA-256

**Severity:** Medium
**Type:** audit identity

**Reproduction**

1. Run the pilot in an environment where `crypto.subtle` is unavailable.
2. Generate or lock a report.
3. Observe the fallback identity begins `local-` and contains an eight-character non-cryptographic hash.
4. Compare this with interface wording promising an immutable SHA-256 report hash.

**Expected:** Report locking fails safely unless SHA-256 is available, or the interface accurately labels a non-cryptographic development identity.
**Actual:** `sha256()` falls back to an FNV-style value while the deliverables list still states SHA-256.

**Recommendation for approval:** Block locking when Web Crypto SHA-256 is unavailable. Suggested message: “This browser cannot create the required SHA-256 report identity.”

### M4 — Evidence is referenced but not packaged

**Severity:** Medium
**Type:** assurance workflow

**Reproduction**

1. Upload an activity with a text evidence reference.
2. Complete review and inspect the report package claims.
3. Observe evidence references and lineage are present, but evidence files are never uploaded or included.

**Expected:** The pilot makes the evidence boundary unmistakable and defines how reviewers access source documents.
**Actual:** The README explains the boundary, but customers may interpret “Evidence and lineage appendix” as including evidence documents.

**Recommendation for approval:** Rename the deliverable to “Evidence-reference and lineage index” unless an approved evidence-file process is added.

### L1 — Scope templates initially contain every guide row

**Severity:** Low
**Type:** usability

**Reproduction**

1. Download a Scope CSV.
2. Open it and observe one guide row per supported governed method.
3. Upload it without deleting unused guide rows.
4. Observe multiple required-field errors.

**Expected:** A first-time user understands which rows to keep.
**Actual:** The instruction exists, but the guide-row model can produce a noisy first validation.

**Recommendation for approval:** Add a first-row instruction or a pre-download category selector. Do not implement until the preferred journey is approved.

### L2 — Prototype role switching may be mistaken for authentication

**Severity:** Low
**Type:** demonstration clarity

**Reproduction**

1. Use the Prototype role selector or complete a workflow hand-off.
2. Observe the application changes roles without credentials.

**Expected:** Workshop attendees understand the selector is a demonstration aid.
**Actual:** The README explains this, but the interface may still prompt security questions.

**Recommendation for approval:** Add visible wording: “Demo role switch — not user authentication.”

### L3 — Customer naming is hard-coded

**Severity:** Low
**Type:** reuse and labelling

**Reproduction**

1. Clear browser-stored customer data.
2. Export a calculation or session file after repopulating the neutral pilot.
3. Observe filenames and some workflow copy remain prefixed with `new-era-group`.

**Expected:** A cleared or reused pilot derives filenames and release copy from the active organisation or a neutral default.
**Actual:** Several export filenames and the final release audit wording are fixed to New Era Group.

**Recommendation for approval:** Decide whether this branch is customer-specific. If reusable, derive a safely slugged organisation label; otherwise document the branch as New Era-only.

## Approval-only wording and interface recommendations

These proposals are not implemented:

1. Replace “Export pilot session” with “Export non-restorable session archive” until restore exists.
2. Replace “Clear all local customer data” with “Clear browser-stored pilot data”.
3. Add “Downloaded files must be deleted separately.” beside the clear control.
4. Add “Demo role switch — not user authentication.” beside the role selector.
5. Replace “Evidence and lineage appendix” with “Evidence-reference and lineage index”.
6. Show reporting year and factor year together wherever results are approved.
7. Keep flagged rows as open controls and use “Resolve or disposition all flagged rows before submission.”
8. Add an organisation-boundary readiness row before report locking.

## Questions New Era is likely to ask

- Why does a 2025 report use 2026 emission factors?
- Is our uploaded information sent to D-carbN or any third party?
- Who can see data stored in the browser profile?
- What happens if the browser cache is cleared or the computer fails?
- Can the exported session be restored on another computer?
- Does Clear Local Data also delete downloaded files?
- Are invoices and evidence documents included in the report package?
- How are rejected or omitted rows recorded?
- Does switching role represent a real user login and approval signature?
- Which Scope 3 categories are supported, estimated or intentionally excluded?
- Can the final hash be independently reproduced?
- Is the output an assured carbon report or a prototype preview?

## Proposed customer demonstration script

1. State the boundary: browser-only, fictional data, no database, no external transmission and not an assured filing.
2. Show Calendar year 2025 and explain that factor-year approval remains open.
3. Show the three guided Scope journeys and download one CSV per scope.
4. Open the fictional files and explain source IDs, units and evidence references.
5. Upload Scope 1, Scope 2 and Scope 3 independently.
6. Demonstrate an intentional duplicate and the correction checklist.
7. Show the calculated fictional results and reproduce the arithmetic.
8. Inspect evidence references, governed method IDs and batch audit events.
9. Demonstrate the contributor-to-analyst-to-approver hand-off while stating that role switching is not authentication.
10. Inspect the report preview, methodology disclosure and SHA-256 identity.
11. Export the results CSV and session archive; explain that the session archive is not currently restorable.
12. Explain the exact deletion boundary without clearing the workshop session unless an export and explicit approval exist.
13. Close with the approval list and confirm that real New Era data will not be loaded yet.

## Proposed customer data-preparation checklist

- [ ] Use only the approved Calendar year 2025 reporting boundary.
- [ ] Assign a stable, unique source record ID to every row.
- [ ] Use only method IDs and exact units from the downloaded template.
- [ ] Confirm activity dates are genuine dates within the reporting period.
- [ ] Provide one evidence reference per activity without attaching confidential files.
- [ ] Reconcile distance, passengers, journeys, rooms, nights and payload components.
- [ ] Separate organisation information from activity uploads.
- [ ] Complete supplier name, methodology, version, boundary and assurance status for supplier-specific results.
- [ ] Complete equipment reference for refrigerant service records.
- [ ] Remove unused guide rows.
- [ ] Check for duplicate IDs across all files and prior uploads.
- [ ] Confirm Scope 3 category ownership and exclusions.
- [ ] Remove names, email addresses, employee identifiers, invoice images and confidential supplier details from pilot files.
- [ ] Obtain Leonard's written approval before moving from fictional to anonymised data.
- [ ] Retain a controlled copy of source files outside the browser pilot.

## Prioritised approval checklist for Leonard

### P0 — required before any real New Era data

- [ ] Approve the reporting-year/factor-year policy and regression baseline.
- [ ] Approve a file-completeness policy for flagged rows.
- [ ] Require organisation metadata before report locking.
- [ ] Approve and test a session restore mechanism.
- [ ] Approve a written data-classification, device-access, retention, deletion and incident protocol.
- [ ] Obtain New Era's informed agreement to the local pilot boundary.

### P1 — required before a controlled anonymised pilot

- [ ] Reject impossible calendar dates.
- [ ] Clarify Clear Local Data and downloaded-file deletion wording.
- [ ] Fail safely when SHA-256 is unavailable.
- [ ] Approve evidence-reference versus evidence-file wording.
- [ ] Approve the exact demonstration script and named facilitator/reviewer roles.

### P2 — presentation improvements

- [ ] Approve Scope-template onboarding changes.
- [ ] Approve demo-role wording.
- [ ] Decide whether customer naming remains hard-coded or becomes reusable.

## Go/no-go recommendation

**Real New Era operational data: NO-GO.**

**Fictional demonstration: GO.**
**Irreversibly anonymised, non-confidential rehearsal data: conditional GO** only after Leonard approves the P1 controls and the handling protocol.

The recommended next decision is to approve the P0 remediation order, beginning with factor-year governance and incomplete-file blocking. Those two controls most directly protect calculation accuracy and inventory completeness.

## Final validation record

| Check | Result |
|---|---|
| JavaScript syntax | Passed |
| CSV structure | Passed for all committed samples |
| JSON structure | Passed |
| Governed-method template coverage | Passed, 22 of 22 methods represented |
| Scope 1/2/3 independent uploads | Passed |
| Duplicate detection | Passed |
| Fictional calculations | Passed against the values listed above |
| Evidence and audit lineage | Passed |
| Results CSV and session export | Passed; restore gap recorded as H3 |
| Report locking and SHA-256 in tested localhost browser | Passed; missing profile control recorded as H4 |
| Browser console | No warnings or errors |
| Secret scan | Passed |
| Personal-contact-information scan | Passed; no emails, phone numbers, employee records or customer contact records in fictional evidence. Leonard appears only as the user-requested approval role. |
| Network/database dependency scan | Passed; CSP retains `connect-src 'none'` |
| Temporary test artifacts | Deleted and absent from the repository |
| Production-file boundary | Passed; branch diff is confined to `local-demo/` |
| `main` | Unchanged |
| Pilot branch separation | Confirmed |

The organisation label “New Era Group” is intentionally present because this is the named customer pilot. It is not accompanied by real customer activity, employee, invoice, supplier-contact or personal-contact information.
