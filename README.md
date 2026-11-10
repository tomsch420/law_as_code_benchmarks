# Law-as-code benchmarks

krrood tried on published law-as-code benchmarks: laws, cases under them and the reference
answer for each case.

`doc/law_as_code_benchmarks.md` surveys the candidates and picks the ones krrood is tried on.

## SARA

`resources/sara/` holds SARA's archive (`sara.tar.gz`, SHA-256 `e4f1b845016fc38b…`) unchanged,
under its MIT license. `src/law_as_code_benchmarks/sara/` reads each case into a domain model of
parties, services and places, and answers it with krrood rules over that model. SWI-Prolog only
expands the facts a case's own Prolog rules generate; SARA's Prolog statutes are never run. Modelled so far: the exclusions from employment of § 3306(c).

Score the test split, with SWI-Prolog (`apt-get install swi-prolog-nox`) on the path:

```bash
pip install -e ".[dev]"
python scripts/score_sara.py
```

| Split | Asks | Correct | Modelled | Cases |
|---|---|---|---|---|
| test | entailment | 14 | 14 | 100 |
| test | amount | 0 | 0 | 20 |

`score_sara.py` also times each stage of answering a modelled case, and SARA's own Prolog program
answering the same test goal with its statutes and the case already loaded. On one local run:

| Stage, per modelled case | Median | Maximum |
|---|---|---|
| expanding the case's facts (SWI-Prolog) | 88 ms | 101 ms |
| reading the domain model | 0.17 ms | 29 ms |
| answering in krrood | 1.7 ms | 1,875 ms |
| answering in SARA's Prolog program | 0.005 ms | 0.03 ms |

The maximum of the krrood stages is the first case, which pays krrood's one-off warm-up.

