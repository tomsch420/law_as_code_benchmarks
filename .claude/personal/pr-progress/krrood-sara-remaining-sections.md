## PR #5 krrood-sara-remaining-sections

### Plan
- Employment tax: rest of § 3306 (employer (a), wages (b), employment (c) + exclusions) and § 3301; 8 test cases
- Stated conclusions (s3306_a, s3306_b, s3306_c, total_wages_employer) read into the domain model and taken as given (standing rule)
- Mirror SARA's quirks: day_to_stamp's +1 day before %W weeks, shared week count across two years, round half away from zero
- Tests first: domain reading, each provision on its 8 cases, scoring

### Done
- Plan split in 4 items (posted on #2); branch, draft PR #5

### Next
- Domain: payments, plans, stated conclusions; reader
- Provisions s3306_a_*, s3306_b_*, s3306_c, s3301
