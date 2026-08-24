# UK 2023 HVO governed methodology

## Purpose and availability

This optional specialist method applies only to evidenced hydrotreated vegetable
oil (HVO) activity dated from 1 January through 31 December 2023. It is
tenant-neutral and is never substituted for diesel or enabled automatically.
New Era Group's FY2024 period starts on 1 November 2023, so its November and
December 2023 activity must use these methods rather than the 2024 methods.

## Governed calculation methods

| Reporting component | Method ID | UK 2023 source factor ID | Factor |
| --- | --- | --- | ---: |
| Scope 1 direct CH4 and N2O | `scope1.mobile_combustion.hvo.litres.uk_2023.v1` | `2_103_1036_8_1` | 0.03558 kgCO2e/litre |
| Scope 3 Category 3 well-to-tank | `scope3.category3.hvo_wtt.litres.uk_2023.v1` | `12_900_1036_8_1` | 0.27844 kgCO2e/litre |
| Biogenic combustion CO2 outside scopes | Report disclosure | `99_103_1036_8_2` | 2.43 kgCO2/litre |

Scope 1 and Scope 3 records must both be entered with matching allocated
litres. Assurance readiness is blocked when either side is missing or when the
quantities differ. Reconciliation is performed separately for each calendar
year, preventing 2023 and 2024 quantities from masking one another.

## Reporting and evidence controls

- Direct CH4 and N2O are reported in Scope 1.
- Well-to-tank emissions are reported in Scope 3 Category 3.
- Biogenic combustion CO2 is disclosed outside Scopes 1, 2 and 3 and excluded
  from the headline inventory total.
- Activity must be dated in 2023 and include evidence identifying the fuel as
  HVO, its quantity, unit, supplier and delivery or usage date.
- The UK Government 2023 final v1.1 factor set must be imported and approved by
  someone other than the importer before calculation.
- Supplier- and feedstock-specific lifecycle evidence should be used when it is
  available and governed.

## Source lineage

- Publication: https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2023
- Final updated flat workbook: `ghg-conversion-factors-2023-flat-file-update.xlsx`
- Workbook version: 1.1, final, updated 20 June 2023 and published 28 June 2023
- SHA-256: `804885cb9d8f02bbb97dcd92b79ca294080ba892ba67e3c95fcfbae52af359a6`
- Methodology: https://assets.publishing.service.gov.uk/media/647f50dd103ca60013039a8a/2023-ghg-cf-methodology-paper.pdf

