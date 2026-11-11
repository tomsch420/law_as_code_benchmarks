## PR #5 krrood-sara-remaining-sections

### Plan
- Employment tax: rest of § 3306 (employer (a), wages (b), employment (c)) and § 3301; 8 test cases
- Stated conclusions held alongside inferred ones (standing rule)
- Follow the reference answers where SARA's program errs (calendar weeks; (c)(2) on cash remuneration)

### Done
- Plan split in 4 items (posted on #2); draft PR #5; bug PR #6 for answer_case.pl dropping library module headers
- employment_tax.py + conclusions, reader for payments/plans/life events/stated facts; 8/8 test cases, 22/22 train cases; 69 tests pass; pushed 0d30062

### Next
- Confirm all 376 cases read and evaluate; update PR description
- Left for later items: dependents/spouses in (b)(2), (b)(10), (c)(10)(A)(ii) (income-tax item); (a)(2)(B), (b)(7), day-only exclusions not modelled
