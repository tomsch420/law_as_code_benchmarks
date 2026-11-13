### Plan
- impot_revenu (CeCILL 2.1, fetched by scripts/fetch_catala_income_tax_tests.py) in krrood; score 27 scopes
- Remaining: TraitementsSalaires Déclarant/FoyerFiscal (11 tests), BNC (4), BIC (3); then scoring registration, CI fetch step, README, unit tests

### Done
- 9 of 27: NombreDeParts 5, ImputationAuxDéficits 1, ProRata 3; pushed at 78a51e8 (stacked on #21)
- Reader: multi-line CLI results, thousand-spaced integers, call results asserted per output, Interface calls as record defaults, multi-arg functions, Argent.somme
- Rules extracted to scratchpad tax_cgi_revenus.txt etc.

### Next
- Wages model (catala/income_tax/wages.py), then BNC, BIC
