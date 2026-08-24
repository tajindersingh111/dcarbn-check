# UK 2025 HVO governed methodology

This optional, tenant-neutral specialist method applies only to evidenced HVO
activity dated in calendar year 2025. It is never substituted for diesel or
enabled automatically.

| Reporting component | Method ID | UK 2025 source factor ID | Factor |
| --- | --- | --- | ---: |
| Scope 1 direct CH4 and N2O | `scope1.mobile_combustion.hvo.litres.uk_2025.v1` | `2_103_1036_8_1` | 0.03558 kgCO2e/litre |
| Scope 3 Category 3 well-to-tank | `scope3.category3.hvo_wtt.litres.uk_2025.v1` | `12_900_1036_8_1` | 0.56439 kgCO2e/litre |
| Biogenic combustion CO2 outside scopes | Report disclosure | `99_103_1036_8_2` | 2.43 kgCO2/litre |

Scope 1 and Scope 3 records require matching allocated litres. Reconciliation
is year-specific. Direct CH4 and N2O are in Scope 1, well-to-tank emissions are
in Scope 3 Category 3, and biogenic combustion CO2 is disclosed outside scopes
and excluded from the headline inventory total.

Activity requires evidence identifying HVO, quantity, unit, supplier and date.
The imported factor set requires independent approval before use.

## Source lineage

- Publication: https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2025
- Final flat workbook: `ghg-conversion-factors-2025-flat-format.xlsx`
- Published: 10 June 2025
- SHA-256: `8bfdb45b81ec4a88e3bdf4584637330f62e6bd09ce1940e654c5d7b7f736de94`
- Methodology: https://assets.publishing.service.gov.uk/media/6846b0870392ed9b784c0187/2025-GHG-CF-methodology-paper.pdf
