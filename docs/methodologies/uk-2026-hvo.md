# UK 2026 HVO governed methodology

This optional, tenant-neutral specialist method applies only to evidenced HVO
activity dated in calendar year 2026. It is never substituted for diesel or
enabled automatically.

| Reporting component | Method ID | UK 2026 source factor ID | Factor |
| --- | --- | --- | ---: |
| Scope 1 direct CH4 and N2O | `scope1.mobile_combustion.hvo.litres.uk_2026.v1` | `2_103_1036_8_1` | 0.03558 kgCO2e/litre |
| Scope 3 Category 3 well-to-tank | `scope3.category3.hvo_wtt.litres.uk_2026.v1` | `12_900_1036_8_1` | 0.56439 kgCO2e/litre |
| Biogenic combustion CO2 outside scopes | Report disclosure | `99_103_1036_8_2` | 2.43 kgCO2/litre |

Scope 1 and Scope 3 records require matching allocated litres and are
reconciled independently for 2026. Direct CH4 and N2O are in Scope 1,
well-to-tank emissions are in Scope 3 Category 3, and biogenic combustion CO2
is disclosed outside scopes and excluded from the headline inventory total.

Activity requires evidence identifying HVO, quantity, unit, supplier and date.
The imported factor set requires independent approval before use.

## Source lineage

- Publication: https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2026
- Corrected final flat workbook: `ghg-conversion-factors-2026-flat-format-revised.xlsx`
- Original publication: 11 June 2026; corrected flat file: 31 July 2026
- SHA-256: `a9a455ab396dae226d510c7be6233748416d490c41a5d20f3dc7a0c45feecd5e`
- Methodology: https://assets.publishing.service.gov.uk/media/6a2940543b15d05a7ce3202e/2026-GHG-conversion-factors-methodology-report.pdf

The July correction replaced zeroes with blanks for unavailable factors in
specific categories. HVO values are unchanged, but governance pins the complete
factor set to the corrected official workbook.
