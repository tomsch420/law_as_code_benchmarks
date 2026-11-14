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
their own names, under `resources/catala/<example>/tests/`. The housing aids reuse
the family benefits model for the right a child gives to family benefits, with the age
limit of 21, or 22 overseas, that article R823-4 of the Code de la construction sets. The fibre connection grant
also keeps `asp/aide_fibre/ocaml/Eligibilite_commune.ml`. That file lists the postal codes
of the communes in the decree's annex, which Catala declares as an external function.

`src/law_as_code_benchmarks/catala/reader.py` reads the test files in Catala's French,
English or Polish syntax. Each test scope gives a scope its inputs, either through a
subscope or by calling the scope, and asserts its outputs. A test that calls a scope and
asserts nothing, as FONPEPS's does, passes when every output of the scope has a value. The
inputs map onto a domain dataclass, and krrood rules answer the outputs. There is one
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
| `asp/bcae7` | crop rotation standard of the 2025 conditionality (BCAE 7), annual and multi-year criteria | 5 | 5 |
| `asp/aide_fibre` | grant for private works connecting to optical fibre, décret n° 2025-674 | 1 | 1 |
| `asp/fonpeps` | FONPEPS hiring grant in the performing arts, décret n° 2019-1011 | 1 | 1 |
| `aides_logement` | French personal housing aids: eligibility | 3 | 3 |

On one local run, answering a test scope in krrood took 7.6 ms at the median and 1,677 ms
at most. The maximum is the first test scope, which pays krrood's warm-up. Catala's own
interpreter was not run for comparison.

## OpenFisca France

OpenFisca France's 93 tests of family allowances (`tests/formulas/af*.yaml` at
`be579829102c`, periods from 2006 to 2026) are under AGPL-3.0, so they are not kept here.
`scripts/fetch_openfisca_tests.py` downloads them to `resources/openfisca/`, which git
ignores. `src/law_as_code_benchmarks/openfisca/` reads each test's situation and maps it
onto the household of the family benefits model above. Values such as `1412.64 / 12`
are evaluated exactly. The model's own provisions answer the test's outputs (`af`,
`af_base`, `af_majoration`, `af_complement_degressif`, `af_taux_modulation`,
`af_coeff_garde_alternee`), and each answer is compared within the test's error margin.

To answer tests from 2006 on, the model now holds:
- the monthly bases from 2006 to 2026 and the minimum wages from July 2005;
- no modulation by resources before July 2015;
- shared residence counting in full before May 2007;
- the age supplement before May 2008, from age 11 at 9 % and from 16 at 16 %;
- the age of 18 that the décret n° 2026-138 sets from March 2026 for children born
  from March 2012.

Score the tests:

```bash
python scripts/fetch_openfisca_tests.py
python scripts/score_openfisca.py
```

| Expected values | Reproduced | Tests |
|---|---|---|
| from published amounts or outside cases | 76 | 88 |
| computed by OpenFisca itself | 4 | 5 |

No test says where its values come from. Five are counted as OpenFisca's own:
`af_2020_04.yaml`, whose comment derives its income from OpenFisca's own ceiling, and the
four shared-residence tests of `af.yaml`, whose values come from no published amount.

The 13 misses come from readings of the model, which follows Catala's:
- **The oldest child** (`af.yaml` 40, 41, 43, 48, 49): with two entitled children, the
  model pays no age supplement for the oldest of *all* the children given, as Catala's
  epilogue picks it. OpenFisca takes the oldest of the entitled children, so a sibling
  of 20 or 21 does not count.
- **The flat allowance after the age limit** (`af.yaml` 27, 28, 29, 33, 41, 49): the
  model pays it for a child who turned 20, as Catala reads it, however long ago. The
  tests pay none for a child of 21.
- **Rounding** (`af_2018_01.yaml` 5, 12, 19): the model rounds the third child's rate
  times the monthly base to the cent before multiplying by the number of children, as
  Catala rounds. With five later children that is 2 or 3 cents short of the CAF's amount,
  just past the margin of 2 cents.
- **A single child overseas** (`af_2020_04.yaml` 1): the model pays the single-child
  rate whatever the resources. OpenFisca halves it in the second bracket.

On one local run, answering a test took 83 ms at the median and 1,420 ms at most, the
first test paying krrood's warm-up.
