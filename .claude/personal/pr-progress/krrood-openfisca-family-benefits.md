### Plan
- OpenFisca's 93 af tests scored with the family benefits model, OpenFisca-computed apart

### Done
- 80 of 93 reproduced (76/88 independent, 4/5 OpenFisca's own); pushed at eddd7db
- Fetch script, YAML reader, exact arithmetic, mapping, scoring, CI steps
- Model extended 2006-2026 (bases, wages, modulation 2015, sharing 2007, age supplement 2008, 2026 reform)
- krrood #964 filed and worked around; #952 guarded via ChildProvision
- 658 tests pass on local krrood and main dcfad8668f; PR description current

### Next
- User to decide: keep Catala's readings (oldest child, flat allowance past 21) or take the CAF's
- Review by the user; CI not yet read
