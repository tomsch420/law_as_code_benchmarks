## PR #14 sara-cases-without-prolog (off main, outside the plan)

### Plan
- Read case files in Python (pyparsing), expand case rules as objects per kind, drop ground_case.pl

### Done
- PrologReader, case_rules.py (6 kinds), UnrecognizedCaseRule; identical facts/order/tests to SWI for all 376 cases
- Train 256/256, test 120/120; 211 tests; reading 7.3 ms median (was 52 ms); README updated; tests changed as agreed; pushed 5ebb7a3; draft PR

### Next
- Not done: reasoning over a recurring payment as one object
