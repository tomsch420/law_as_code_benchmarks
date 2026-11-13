### Plan
- impot_revenu (CeCILL 2.1, fetched by scripts/fetch_catala_income_tax_tests.py) in krrood; score 27 scopes
- Remaining: BNC (benefices_non_commerciaux, 4 tests) and BIC (benefices_industriels_commerciaux, 3); then scoring registration, CI fetch step, README, unit tests, PR body

### Done
- 20 of 27: NombreDeParts 5, déficits 1, prorata 3, TraitementsSalaires 11; pushed at 1b72e2e (stacked on #21)
- Reader/scope tests: multi-line CLI results, call results per output, Interface calls as defaults, interface subscopes, merged scope bodies, negative money, Argent.somme incl. mapped field

### Next
- BNC model catala/income_tax/non_commercial.py, then BIC
