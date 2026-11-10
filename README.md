# Law-as-code benchmarks

krrood tried on published law-as-code benchmarks: laws, cases under them and the reference
answer for each case.

`doc/law_as_code_benchmarks.md` surveys the candidates and picks the ones krrood is tried on.

## SARA

`resources/sara/` holds SARA's archive (`sara.tar.gz`, SHA-256 `e4f1b845016fc38b…`) unchanged,
under its MIT license. `src/law_as_code_benchmarks/sara/` loads each case and answers it with
krrood rules: SWI-Prolog only expands the facts a case's own Prolog rules generate, and every
answer comes from krrood. Modelled so far: the exclusions from employment of § 3306(c).

Score the test split, with SWI-Prolog (`apt-get install swi-prolog-nox`) on the path:

```bash
pip install -e ".[dev]"
python scripts/score_sara.py
```

| Split | Asks | Correct | Modelled | Cases |
|---|---|---|---|---|
| test | entailment | 14 | 14 | 100 |
| test | amount | 0 | 0 | 20 |
