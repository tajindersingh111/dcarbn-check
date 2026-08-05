# Synthetic staging test-data plan

## Rules

- Use only fictional organisations, people, vehicles and transactions.
- Use `example.invalid` for email and internet identifiers.
- Prefix all external identifiers with `UAT-`.
- Do not copy customer, DVLA, telematics or production records into staging.
- Record the fixture version in every UAT evidence pack.
- Delete and recreate the tenant when a clean baseline is required.

## Baseline dataset

| Entity | Quantity | Purpose |
|---|---:|---|
| Tenants | 2 | Prove isolation |
| Users | 7 per primary tenant | Exercise each system role |
| Organisations | 2 | Parent and operating-company scenarios |
| Vehicles | 4 | Diesel, petrol, battery-electric and unknown/malformed |
| Shipments | 6 | Domestic logistics sample |
| Journeys | 8 valid + 2 invalid | Distance validation and row-level errors |
| Fuel records | 6 | Litres and kWh inputs |
| Payload records | 4 | Tonne-kilometre lineage |
| Operational emissions | 4 | DATa review and classification |
| Inventories | 2 | Draft and approval/locking workflows |
| Activities | At least 6 | Scope 1, Scope 2 and Scope 3 category 4 |

## Dynamic identifiers

The operator must capture generated tenant, organisation, inventory, factor-set and activity UUIDs in the UAT evidence log. Replace placeholders such as `<organisation_uuid>` only in local working copies; never commit generated staging identifiers or credentials.

## Negative data

Include deliberately invalid records:

- journey distance without a unit;
- Scope 3 activity without a category;
- Scope 2 activity without a location/market method;
- duplicate source record and idempotency key;
- unmapped external customer;
- zero/negative fuel quantity;
- invalid country code;
- attempted record access using a different tenant.

## Reconciliation

After imports, reconcile submitted, accepted and rejected counts against the API batch response. Totals must also reconcile by source record ID, vehicle, journey, organisation, scope and reporting period.
