# New Era browser-pilot final rehearsal

Date: 18 August 2026

Branch: `agent/new-era-browser-pilot`

Starting commit: `77f890bbe3b9fd7042a43d16b39e7c2d1bd0c2d7`

Data classification: fictional 2025 data only. No real customer, contact or
commercially sensitive information was used. The ephemeral rehearsal passphrase
is deliberately not recorded.

## Outcome

The complete browser-local customer journey passed from an empty encrypted
session through independent organisation, Scope 1, Scope 2 and Scope 3 uploads,
validation, analyst approval, encrypted recovery and immutable report locking.

| Control | Rehearsal evidence | Result |
|---|---|---|
| Scope uploads | Organisation and each scope CSV validated independently; three activities accepted | Pass |
| 2025 methodology | DESNZ pack `desnz-uk-ghg-2025.v1`, version `2025.1`, year and source displayed for every result | Pass |
| Invalid/duplicate blocking | Impossible date and repeated ID produced two flagged rows and zero imports; an existing source ID was also rejected | Pass |
| Readiness integrity | Empty session showed 13%; flagged session showed 25%; submit remained disabled until all blockers cleared, then reached 100% | Pass |
| Organisation metadata | Removing the organisational boundary disabled lock and displayed the precise release-control failure | Pass |
| Calculation/evidence lineage | Scope results, source IDs, evidence references, activity values, factors and approval statuses remained linked | Pass |
| Audit and exports | Calculation CSV action completed; generated report contained the complete factor pack and 10 audit events before recovery | Pass |
| Encrypted recovery | Version 1 AES-GCM portable envelope contained no organisation plaintext; correct-passphrase restore returned all three activities and the same report hash | Pass |
| Failure handling | Incorrect passphrase and modified ciphertext both returned the same safe rejection message | Pass |
| Local controls | Clear Local Data removed the prior session and returned to passphrase setup; forced 16-minute inactivity state locked and recovered correctly | Pass |
| Immutable report | Generated v1 snapshot and locked v2 release retained the same 64-character SHA-256 identity | Pass |

## Verified calculation results

| Scope | Fictional activity | Factor | Result |
|---|---|---:|---:|
| Scope 1 | 10,000 gross-CV kWh natural gas | 0.18296 | 1,829.60 kgCO₂e |
| Scope 2 | 50,000 kWh UK electricity | 0.17700 | 8,850.00 kgCO₂e |
| Scope 3 | 1,000 passenger-km national rail | 0.03546 | 35.46 kgCO₂e |
| **Total** | | | **10,715.06 kgCO₂e** |

Final report evidence:

- Status: `Locked customer release`
- Version: `2`
- SHA-256: `2eee8a7546e99d87be4d81a7f7e6f901b6b659cb66680cb76610f71142c991b0`
- Audit events after restore and lock: `12`
- Final event: report v2 locked and released to New Era Group

## Rehearsal finding resolved

The report lock already failed correctly when organisation metadata was missing,
but the adjacent Final controls card incorrectly displayed “Ready for locking”.
The card now derives its status and detailed messages from the full release-check
set. A regression assertion protects that behaviour.

## Recommendation

**GO** for the agreed controlled New Era browser pilot using fictional or
irreversibly anonymised 2025 data and the approved passphrase, browser-security
and demonstration protocol.

**NO-GO** remains in force for identifiable, personal, confidential or
commercially sensitive data. Those data require the future hosted controls,
including managed identity, tenant isolation, central audit, retention and an
agreed processing/security basis.
