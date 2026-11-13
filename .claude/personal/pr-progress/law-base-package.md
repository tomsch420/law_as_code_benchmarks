### Plan
- Base package law_as_code_benchmarks.law for what SARA, Catala and OpenFisca share: Period, Conclusion/AssessedCase/Provision, scoring

### Done
- law/period.py, law/provision.py, law/scoring.py with tests/law; SARA, Catala and OpenFisca moved onto them; pushed at 8ce0192 as draft PR #24 (stacked on #23)
- SARA Period bounds renamed to first_day/last_day (user's choice); scoring included (user's choice)
- tests: sara 224, catala 707, openfisca+law 44; pre-commit passes

### Next
- Review by the user
