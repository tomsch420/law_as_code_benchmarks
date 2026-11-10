## PR #4 krrood-sara

### Plan
- Narrowed in session: loading, scoring and the § 3306(c) exclusions; other sections are item krrood-sara-remaining-sections

### Done
- SARA archive committed; cases loaded via swipl (ground_case.pl); world model
- § 3306(c)(6), (7), (10)(B), (11), (16), (B), (1)(B) as EQL rules: 14/14 test cases correct
- Review round 1: domain model (domain.py, case_reader.py) replaces the Prolog-shaped Event; 42 tests pass; pushed 5dac7c2; threads replied and resolved

### Next
- Watch CI's first run on the PR (not yet seen)
- User to install swi-prolog-nox locally for tests
