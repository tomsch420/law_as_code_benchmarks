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

## Catala examples

`resources/catala/` holds the test files of the examples modelled from
[catala-examples](https://github.com/CatalaLang/catala-examples) at `9e251b932288`, under
its Apache-2.0 license, all unchanged. The three family benefits files are in
`resources/catala/tests/`, renamed after the directories they came from:
`allocations_familiales/tests/tests_allocations_familiales.catala_fr`,
`allocations_familiales/tests/tests_ouverture_droits.catala_fr` and
`prestations_familiales/tests/tests_ouverture_droits.catala_fr`. The other examples keep
their own names, under `resources/catala/<example>/tests/`.

`src/law_as_code_benchmarks/catala/reader.py` reads the test files in Catala's French,
English or Polish syntax. Each test scope gives a scope its inputs and asserts its outputs.
The inputs map onto a domain dataclass, and krrood rules answer the outputs. There is one
provision for each variable of Catala's scopes. A default and its exceptions become a rule
tree: rules of equal standing form an else-if chain of `alternative`s that ends in
Catala's default, and an exception to a single rule is a `refinement` of it. Amounts in
force on a date, such as the family benefits' monthly base, minimum wage, resource
ceilings and Mayotte's rates, are dated values, each carrying its legal source. Money is
in cents, rounded as Catala rounds it.

Score the tests:

```bash
python scripts/score_catala.py
```

| Example | Law | Reproduced | Test scopes |
|---|---|---|---|
| `allocations_familiales`, `prestations_familiales` | French family benefits | 16 | 16 |
| `droit_successions` | reserved portion of an estate, Code civil art. 912–917 | 4 | 4 |
| `polish_taxes` | Polish tax on civil-law transactions, art. 7 | 8 | 8 |
| `us_tax_code` | United States Internal Revenue Code §§ 121 and 132 | 9 | 9 |
| `NSW_community_gaming` | permitted gaming activities of New South Wales | 25 | 25 |

On one local run, answering a test scope in krrood took 7.5 ms at the median and 1,802 ms
at most. The maximum is the first test scope, which pays krrood's warm-up. Catala's own
interpreter was not run for comparison.
