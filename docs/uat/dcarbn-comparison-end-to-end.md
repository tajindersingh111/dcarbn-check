# DcarbN comparison end-to-end UAT

This pack validates the governed customer journey introduced by issue #24.

## Golden customer journeys

| Journey | Confirmed classification | Government method | Expected comparison |
|---|---|---|---|
| Owned Class I diesel van | Scope 1 mobile combustion | Class I diesel van kilometres, UK 2026 | DcarbN higher |
| Third-party inbound shipment | Scope 3 Category 4 | Diesel van tonne-kilometres, UK 2026 | DcarbN lower |
| Third-party outbound shipment | Scope 3 Category 9 | Average diesel van tonne-kilometres, UK 2026 | Equal |
| Shipment without activity inputs | Scope 3 Category 9 | No defensible match | Structured comparison unavailable |

The versioned source fixture is
`docs/uat/fixtures/dcarbn-operational-emissions-v2.json`.

## Automated release evidence

The backend UAT test proves:

- schema 2.0 parsing and stable import idempotency;
- unique external activity keys and source hashes;
- reviewer-controlled Scope 1, Category 4 and Category 9 routing;
- exact governed Government method selection;
- equal, higher, lower and zero-baseline delta behaviour;
- a structured unavailable path when comparator inputs are insufficient;
- deterministic locked-report hashing;
- source-record changes alter the locked snapshot hash;
- the comparator remains excluded from inventory totals.

Existing API, UI and export suites additionally prove tenant scoping, side-by-side
customer presentation, methodology lineage and deterministic PDF/CSV disclosure.

## Customer acceptance sequence

1. Import the fixture using the operational-emissions schema 2.0 endpoint.
2. Repeat the same batch with the same idempotency key and confirm no duplicate.
3. Review and confirm each suggested classification.
4. Convert each approved record into its inventory.
5. Generate the governed UK Government comparator.
6. Confirm exactly one result is included in inventory totals.
7. Approve and lock the inventory.
8. Generate the audit report and download PDF and CSV.
9. Confirm both calculations, their versions, delta, reporting basis and lineage.
10. Confirm the Government value is labelled disclosure-only and does not imply endorsement.
11. Re-download the locked report and confirm the report SHA-256 is unchanged.

## Release gate

The tranche may merge only when CI and supply-chain security both pass. Any failed
customer journey, duplicate total, missing lineage field or changed locked-report
hash is release-blocking.
