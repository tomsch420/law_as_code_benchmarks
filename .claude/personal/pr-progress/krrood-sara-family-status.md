## PR #7 krrood-sara-family-status

### Plan
- §§ 7703, 152, 151, 2 and 68(b) in family_status.py; goals asked as EQL queries in goal.py
- Stacked on this branch: #8 krrood-sara-taxable-income, then #9 krrood-sara-income-tax

### Done
- 36/36 test cases; 122 tests pass at 92cce26; merged up into #8 and #9
- Review thread on provision.py:335 (reuse EQL bindings): goals now one EQL query (GoalQuery), Bindings/unify removed; replied and resolved
- Filed cram2/cognitive_robot_abstract_machine#937 (variable reused in two exists)

### Next
- Open: s152_d_1_B_pos (party named only in the question)
