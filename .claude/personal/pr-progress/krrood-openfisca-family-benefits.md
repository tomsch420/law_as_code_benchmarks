### Plan
- Fetch script for OpenFisca's 5 af*.yaml files (93 tests) at be579829102c, git-ignored
- YAML reader (pyyaml) with exact arithmetic expressions; map onto Household
- Extend dated amounts/rules 2006-2026; map outputs af, af_base, af_majoration, ...
- Score within margin, OpenFisca-computed (af_2020_04 + 4 shared-residence tests) apart

### Done
- Draft PR #18 open; pyyaml and the hand-kept split agreed with the user

### Next
- Fetch script and reader, test-first
