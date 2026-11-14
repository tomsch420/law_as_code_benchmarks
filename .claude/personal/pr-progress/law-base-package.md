### Plan
- Base package law_as_code_benchmarks.law for what SARA, Catala and OpenFisca share

### Done
- Period, Conclusion/AssessedCase/Provision, scoring (8ce0192); rounding and FetchedTestFile (c4f55e9)
- Review: Period subclasses krrood Bounds[date | None], fields lower/upper (dff7600); comment answered, not resolved
- PR #24 based on main after #19-#23 merged; description current
- tests: sara 212, openfisca 32, law 20; catala 706 + 3 failing from krrood's 2026-11-14 commits (also failing before this change)

### Next
- User review; krrood-caused Catala failures; possible Catala-internal follow-ups (brackets, adding years to dates)
