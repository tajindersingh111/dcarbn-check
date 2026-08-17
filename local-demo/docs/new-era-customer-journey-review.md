# New Era browser-pilot customer-journey remediation review

Review date: 18 August 2026

Branch: `agent/new-era-browser-pilot`

Baseline: `d658801ce5fa5bfaa16eb8610bed54aa7bd75e33`

Data used: fictional test data only

## Executive outcome

The five High findings have been remediated in the database-free, network-disabled
browser pilot. The pilot is suitable for a controlled anonymised-data rehearsal
after Leonard accepts the residual limitations below. It is **not approved for
identifiable, personal, confidential or commercially sensitive New Era data**.

## Finding status and evidence

| Finding | Status | Implemented control | Evidence |
|---|---|---|---|
| H1 — factor provenance | Remediated | Explicit DESNZ 2025 pack `2025.1`; year/version/source per result; unsupported years and unavailable factors fail closed | Factor coverage, three known-output regressions, year and closed-loop rejection tests |
| H2 — flagged data progression | Remediated | Whole-file rejection; persistent duplicate/unresolved state; organisation and independent Scope 1/2/3 validations plus confirmations required | Blocker matrix and corrected re-upload journey |
| H3 — session recovery | Remediated | Complete, versioned AES-GCM export with PBKDF2-SHA-256 and an encrypted SHA-256 checksum | Round trip, plaintext absence, wrong-passphrase, corruption and incompatible-version tests |
| H4 — report lock | Remediated | Organisation, period, boundary, scopes, contributor, evidence, approvals and method lineage required; precise open controls displayed | Lock-blocker matrix and locked-report journey; 64-character SHA-256 identity |
| H5 — browser-local security | Remediated | AES-GCM local storage, memory-only passphrase, legacy migration, 15-minute lock, explicit clear, encrypted export only, `connect-src 'none'` | Storage inspection, source scans and clear/reload journey |

## Reproduction and expected-versus-actual record

1. Open `http://127.0.0.1:8081/` in a clean browser. Expected/actual: the
   security gate appears before data and requires a 12-character passphrase.
2. Confirm `Calendar year 2025`, then upload
   `sample/fictional-organisation-2025.csv` and the three fictional scope files.
   Expected/actual: the four readiness blockers clear independently.
3. Re-upload a source ID already accepted. Expected/actual: no rows import; a
   precise duplicate blocker remains until a corrected clean file is validated.
4. Use the unavailable broad closed-loop method. Expected/actual: calculation
   fails with the official-2025-factor explanation; no nearby factor is chosen.
5. Attempt submit with any missing file, unresolved row or unchecked confirmation.
   Expected/actual: submit is disabled and the exact blockers are displayed.
6. Attempt lock with missing boundary, scopes, contributor, evidence confirmation,
   analyst approval or method lineage. Expected/actual: lock remains disabled and
   the missing control appears in Final controls.
7. Export, clear and restore the encrypted session. Expected/actual: activities,
   calculations, audit, workflow and report identity round-trip exactly. Wrong
   passphrases, modified ciphertext and incompatible versions are rejected.

## Issues remaining

- Critical: **0**
- High: **0 open** (the five reviewed findings are remediated)
- Medium: **2**
  1. Browser-local passphrases have no managed recovery or central revocation.
  2. Browser-local audit/locking is demonstrative, not server-enforced tenant
     isolation or append-only audit.
- Low: **2**
  1. Unsupported spend, water, rent and material-specific recycling routes remain
     intentionally excluded until a governed method is approved.
  2. Inactivity lock does not replace locking the operating-system account.

## Interface wording and customer questions

Approved wording includes “Browser-local pilot · encrypted fictional data · no
network connection”, “Nothing was imported. Correct every flagged row and
re-upload the complete file”, and the non-oracular restore error “The passphrase
is incorrect or the encrypted session file is corrupted.”

Likely questions:

- **Does D-carbN receive this upload?** No; CSP blocks connections and no network
  client exists.
- **Where is data held?** In an encrypted envelope in this browser profile and
  any encrypted export the user chooses to download.
- **Can D-carbN recover the passphrase?** No; it is not stored or transmitted.
- **Why was my row blocked?** The UI identifies the duplicate, date, unit,
  evidence, lineage or unavailable-factor condition.
- **Is this an assured filing?** No; this is a governed pilot calculation.

## Proposed demonstration script

1. Explain the browser-local boundary and passphrase responsibility.
2. Show the 2025 factor-pack identity and download a scope template.
3. Demonstrate a duplicate failure, correction and clean re-upload.
4. Upload all four fictional files and show submission blockers clearing.
5. Walk through contributor, analyst and approver roles.
6. Inspect factor lineage, export calculation CSV and lock the SHA-256 report.
7. Export encrypted session, clear locally, and restore it.
8. Restate the later hosted identity, tenant and managed-audit requirements.

## Customer data-preparation checklist

- Use only fictional or approved irreversibly anonymised records.
- Keep supplied headings and assign a stable, unique source ID to each row.
- Keep dates within 1 January–31 December 2025.
- Use only the supplied governed method ID and exact unit.
- Reference evidence with non-personal identifiers; do not embed files.
- Complete boundary, scopes, contributor role and evidence confirmation.
- Remove names, emails, phones, addresses, account numbers, confidential terms
  and personal free text.
- Agree who holds the passphrase and encrypted export.
- Keep any source-to-anonymised mapping outside the pilot under New Era controls.

## Go/no-go and Leonard approval checklist

**Conditional GO** for fictional or irreversibly anonymised rehearsal data after
Leonard approves this review and New Era accepts the browser-local limitations
and passphrase protocol. **NO-GO** for identifiable, personal, confidential or
commercially sensitive data until hosted identity, tenant isolation, managed
retention, central audit and the appropriate processing/security basis exist.

Leonard should approve, in order:

1. The 2025 factor pack and unavailable-factor fail-closed rule.
2. The four-file submission gate and whole-file rejection policy.
3. Passphrase ownership, no recovery and the 15-minute lock.
4. Organisation/evidence/methodology report-lock requirements.
5. The anonymisation checklist and sensitive-data prohibition.
6. The demonstration script and customer wording.
7. Recorded customer acknowledgement before an anonymised rehearsal.

## Final validation scope

The validation record covers JavaScript syntax; factor, blocker and encryption
regressions; CSV/JSON parsing; template coverage; secret and personal-information
scans; network/database dependency scans; browser-console checks; clear/reload
and restore behaviour; and complete diff review. The completion report records
the exact results and commit SHA.
