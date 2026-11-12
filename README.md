# Law-as-code benchmarks

krrood tried on published law-as-code benchmarks: laws, cases under them and the reference
answer for each case.

`doc/law_as_code_benchmarks.md` surveys the candidates and picks the ones krrood is tried on.

## SARA

`resources/sara/` holds SARA's archive (`sara.tar.gz`, SHA-256 `e4f1b845016fc38b…`) unchanged,
under its MIT license. `src/law_as_code_benchmarks/sara/` reads each case file in Python, expands
the rules a case states its facts with (`case_rules.py`), builds a domain model of parties,
events and places, and answers the case with krrood rules over that model. SARA's Prolog
statutes are never run to answer a case. All nine sections are modelled.

Score the test split:

```bash
pip install -e ".[dev]"
python scripts/score_sara.py
```

SWI-Prolog (`apt-get install swi-prolog-nox`) is needed only to time SARA's own Prolog program
on the same cases, for comparison.

| Split | Asks | Correct | Cases |
|---|---|---|---|
| test | entailment | 100 | 100 |
| test | amount | 20 | 20 |
| train | entailment | 176 | 176 |
| train | amount | 80 | 80 |

SARA's own program, run on SWI-Prolog 9.0.4, gives the reference answer in 105 of the 120 test
cases. `score_sara.py` also times each stage of answering a case. On one local run:

| Stage, per test case | Median | Maximum |
|---|---|---|
| reading the case file | 7.3 ms | 121 ms |
| reading the domain model | 0.16 ms | 95 ms |
| answering in krrood | 32 ms | 2,172 ms |
| answering in SARA's Prolog program | 0.03 ms | 44 ms |

The maximum of the krrood stages is the first case, which pays krrood's one-off warm-up.
