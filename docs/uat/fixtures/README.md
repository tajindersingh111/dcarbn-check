# UAT fixtures

These JSON files are fictional examples matching the DATa batch request contracts. They contain no credentials, personal information or genuine vehicle registrations.

Before use:

1. Create the UAT tenant and organisation.
2. Map `UAT-CUSTOMER-001` to the generated organisation UUID.
3. Submit each file to its corresponding `/api/v1/data/*/batch` endpoint using an authorised integration account.
4. Preserve the API response and reconciliation result as UAT evidence.
5. Repeat one batch with the same idempotency key and confirm it does not duplicate records.

The `journeys-invalid.json` fixture must be rejected because it supplies a distance without a distance unit.
