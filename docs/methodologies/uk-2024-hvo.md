# UK 2024 HVO governed methodology

## Purpose and availability

This is an optional specialist method for organisations that used hydrotreated
vegetable oil (HVO) in the 2024 calendar year. New Era Group is the first test
case, but the method is not tenant-specific. It is available to any customer
only when HVO is explicitly selected and evidence confirms that the fuel was
HVO. It is never substituted for diesel automatically.

## Governed calculation methods

| Reporting component | Method ID | UK 2024 source factor ID | Factor |
| --- | --- | --- | ---: |
| Scope 1 direct CH4 and N2O | `scope1.mobile_combustion.hvo.litres.uk_2024.v1` | `2_103_1036_8_1` | 0.03558 kgCO2e/litre |
| Scope 3 Category 3 well-to-tank | `scope3.category3.hvo_wtt.litres.uk_2024.v1` | `12_900_1036_8_1` | 0.559 kgCO2e/litre |
| Biogenic combustion CO2 outside scopes | Report disclosure | `99_103_1036_8_2` | 2.43 kgCO2/litre |

The direct and well-to-tank records must both be entered using the same
allocated litres. The report cannot claim assurance readiness if either record
is absent or the litres do not reconcile.

## Reporting treatment

The UK Government methodology treats CO2 released at the point of biofuel use
as biogenic. The Scope 1 factor therefore contains direct methane and nitrous
oxide only. Upstream production and distribution are reported in Scope 3
Category 3. Combustion CO2 is shown separately outside Scopes 1, 2 and 3 and is
excluded from the headline inventory total.

The Government well-to-tank factor uses UK-average Renewable Transport Fuel
Obligation data. Supplier- and feedstock-specific lifecycle evidence should be
used when it is available and governed.

## Evidence and period controls

- Activity date must fall between 1 January and 31 December 2024.
- A delivery note, invoice, supplier declaration or equivalent evidence must
  identify the fuel as HVO.
- Evidence should identify quantity, unit, supplier and delivery/usage date.
- The UK 2024 final v1.1 factor set must be imported and independently approved.
- A fiscal-year inventory containing 2023 activity cannot use the UK 2024
  method for those 2023 records; the applicable 2023 factors must be governed
  separately.

## New Era demonstration value

For the test quantity of 976,227 litres:

- Scope 1: 34,734.15666 kgCO2e
- Scope 3 Category 3 well-to-tank: 545,710.893 kgCO2e
- Total included in the Scope 1–3 headline: 580,445.04966 kgCO2e
- Biogenic CO2 disclosed outside scopes: 2,372,231.61 kgCO2

These are deterministic demonstration calculations from the official UK 2024
factors. They must be reconciled to New Era's source documents and reporting
boundary before being treated as final customer results.

## Sources

- UK Government 2024 conversion factors: https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024
- UK Government methodology paper: https://assets.publishing.service.gov.uk/media/66a9fe4ca3c2a28abb50da4a/2024-greenhouse-gas-conversion-factors-methodology.pdf
