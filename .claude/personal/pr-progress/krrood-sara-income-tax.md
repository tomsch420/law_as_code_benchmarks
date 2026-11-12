## PR #9 krrood-sara-income-tax (stacked on #8, #7; merges bug PRs #10, #11)

### Plan
- § 1 schedules and brackets, § 1(a)-(d), § 1, tax; score all 120 test cases

### Done
- 120/120 test cases (100 entailment, 20 amounts); train: all modelled correct but s152_d_1_B_pos
- years_in_question (tax_case_9 226 s -> 4 s); tests changed as agreed; 167 tests pass; merged #7's EQL goal queries at 10142be, score unchanged; pushed

### Next
- Open, not needed by any case: § 3306(b)(2), (b)(10) for dependents and spouses; 32 train cases of folded § 3306 predicates
