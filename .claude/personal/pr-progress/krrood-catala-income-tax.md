### Plan
- impot_revenu (CeCILL 2.1, so fetched by script like OpenFisca) in krrood: NombreDeParts, ImputationAuxDéficitsLesPlusAnciens, ProRataArrondiEuroBranchement (oracles in Python), TraitementsSalaires Déclarant/FoyerFiscal, BNC, BIC; score 27 scopes
- Expected values are in catala-test-cli blocks (whole call results as structures); stacked on #21 for the framework

### Done
- Branch stacked on krrood-catala-housing-ownership-and-residences, PR #22 retargeted
- Reader: multi-line CLI results, integers with thousand spaces, a printed call result becomes one assertion per output (uncommitted)
- Rules extracted to scratchpad tax_*.txt (cgi_revenus 82 blocks)

### Next
- Fetch script + resources/catala_impot_revenu gitignored; package catala/income_tax/; scope by scope
