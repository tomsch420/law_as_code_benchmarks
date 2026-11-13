# Law-as-code benchmarks for krrood

A survey of published benchmarks that state a law, cases under it and the reference answer for
each case. It ends by picking the ones krrood is tried on. Every figure below was read from the
benchmark's own files or pages on 2026-11-09, at the commit or archive named in *Sources*.

## What krrood is tried for

krrood is meant to state a law's rules over Python objects and answer what they imply. A
benchmark is useful when it tests that, and not reading natural language:

- **Structured facts.** A case whose facts are given as data can be loaded as objects. A case
  given only as prose needs an extraction step first, and then the score measures that step.
- **Exceptions.** Rules that a later or more specific rule overrides, as statutes are written.
- **Dated validity.** The same question answered differently depending on the date, because
  amounts or rules changed.
- **Computation.** An amount to compute, not only a yes or no.
- **Ground truth from outside.** A reference answer that does not come from the very code
  being tested.
- **A license that lets the cases be kept** in this repository, or at least fetched by a script.

## The candidates

| Benchmark | License | Size | Facts given as | Asks | Exceptions | Dated validity | Ground truth |
|---|---|---|---|---|---|---|---|
| SARA | MIT-style, dataset | 9 sections of the United States Internal Revenue Code; 376 cases (256 train, 120 test): 276 entailment, 100 tax amounts | prose **and** Prolog facts per case | yes/no, and an amount of tax | yes: § 2, § 63, § 151, § 152, § 3306 and § 7703 state exceptions | by tax year; § 63 and § 68 state 2018–2025 rules | hand-written Prolog program; every case is a runnable query |
| Catala examples | Apache-2.0 | 12 examples, about 44,000 lines of Catala; 129 test scopes | Catala values | amounts, eligibility | central: 273 `exception` in housing benefits, 62 in family benefits | yes: `date_courante` selects rules and amounts year by year | tests written by the authors; family benefits compared with the official simulator by them |
| OpenFisca France YAML tests | AGPL-3.0 | 843 test files; 4,064 parameter files | YAML entities and inputs | amounts per period | implicit, in formulas | central: every parameter is dated, every test names its period | mixed: official simulators for some, regression values computed by OpenFisca for others |
| LegalBench rule tasks | per task; the rule tasks are CC BY 4.0 | 162 tasks; rule-application ones of 47 to 300 test cases (diversity jurisdiction 6 × 300, hearsay 94, personal jurisdiction 50, successor liability 47, telemarketing sales rule 47, UCC or common law 94) | prose | yes/no | some (successor liability is an exception to a rule) | no | hand-labelled answers; includes SARA as `sara_entailment` and `sara_numeric` |
| COLIEE, statute tasks 3 and 4 | signed memorandum; use outside the competition allowed, redistribution not granted | Japanese bar-exam questions over the Japanese Civil Code; size not stated on the corpus page | prose; Japanese for 2026, English only in the 2025 archive | yes/no entailment, plus relevant articles | yes, as the Civil Code has them | no | the bar exam's answers and the articles that settle them |
| DMN TCK | Apache-2.0 | 155 test models (29 at compliance level 2, 122 at level 3) | DMN XML inputs | decision outputs | hit policies only | no | expected results agreed by the vendors |
| PROLEG | none found | Civil Code rule base checked against bar exams 2009–2022, per its authors | Prolog facts | judgments | central (presupposed ultimate fact theory) | no | the bar exams |

### SARA

The StAtutory Reasoning Assessment of Holzenberger, Blair-Stanek and Van Durme (2020). Nine
sections of the Internal Revenue Code (§ 1, § 2, § 63, § 68, § 151, § 152, § 3301, § 3306,
§ 7703), simplified, in prose and in Prolog. Each case is a Prolog file holding the prose facts
as a comment, the facts as Prolog terms over events with start and end dates, and the test as a
query: `s151_a(alice,4000,2015)` for an entailment case, `tax(alice,2006,66088)` for a
numerical one. The Prolog program decides every case, so the reference answers can be checked,
and a krrood model can be loaded from the same facts with no language step.

### Catala examples

Laws written in Catala by its authors and contributors: French family benefits (*allocations
familiales*), housing benefits (*aides au logement*), income tax, inheritance law, Polish
taxes, New South Wales community gaming, § 121 and § 132 of the United States tax code, and
three aids paid by the French payment agency (ASP): the crop rotation standard of the
agricultural conditionality, a grant for connecting to optical fibre and a hiring grant in
the performing arts. Catala states a
law as a default with exceptions that override it, which is the construct krrood's rules have
to express. The family benefits example holds rules and amounts from 2011 to 2023, chosen by
the date a computation is for; its 15 tests ask about dates from 2019 to 2022. Its authors
compared it with the official simulator, mes-droits-sociaux.gouv.fr, and found a case OpenFisca
got wrong: the income cap that `L755-12` of the *Code de la sécurité sociale* lifts for
single-child families overseas (Merigoux, Chataing and Protzenko 2021, section 6).

### OpenFisca France

The French tax and benefit system as OpenFisca formulas, with a dated value for every
parameter and YAML tests stating inputs, a period and the expected output. 93 of the tests are
for family benefits, with periods from 2006 to 2026, including the 2026 reform raising the age
of the increase (`af_majoration_age_2026.yaml`). The family benefits are the law Catala's
example states too, so the two reference implementations can be checked against each other. Many
expected values were produced by OpenFisca itself and only guard against regressions. AGPL-3.0
asks that whatever is kept here of it stays under the same license, so a script fetches the
tests rather than copying them.

### LegalBench rule tasks

A benchmark for language models. The rule-application tasks give a fact pattern in prose and
ask whether a rule is met. Modelling them in krrood means extracting facts from prose first; the
diversity jurisdiction tasks are the exception, being generated from one template each (parties,
their citizenships and the amount in controversy). Its statutory tasks are SARA's.

### COLIEE statute tasks

The Competition on Legal Information Extraction and Entailment asks whether a bar-exam statement
follows from Civil Code articles. Tasks 3 and 4 are language understanding over Japanese text;
the data is had by signing a memorandum and comes without a right to redistribute.

### DMN TCK

The Decision Model and Notation conformance kit tests whether an engine evaluates decision
tables and FEEL expressions as the standard says. It holds no law. It would matter if krrood were
to import DMN models, which no item asks.

### PROLEG

Satoh's Prolog system for the Japanese presupposed ultimate fact theory, with a rule base over
the Civil Code. No public distribution of the system, its rule base or its cases was found.

## The pick

1. **SARA.** Facts already structured, reference answers checkable by running the Prolog
   program, a permissive license, exceptions and tax years. Its license lets the 376 cases
   be kept here. The score is the share of cases answered as the Prolog program answers them,
   apart for entailment and amounts, on the published test split.
2. **Catala's family benefits** (`allocations_familiales` with `prestations_familiales` and
   `base_mensuelle_allocations_familiales`). Exceptions with priority and amounts chosen by
   date, under Apache-2.0. The score is the share of its tests reproduced.
3. **OpenFisca France's family benefit tests** (`tests/formulas/af*.yaml`), fetched by a
   script. The same law as the second pick, over twenty years of dated parameters, so it
   tests dated validity where Catala's tests cover four. The score is the share of the 93 tests
   reproduced within each test's stated error margin, reported apart for tests whose values
   OpenFisca computed itself.

Not picked: LegalBench's rule tasks and COLIEE measure reading prose; the DMN TCK holds no
law; PROLEG is not available. LegalBench's diversity jurisdiction tasks could be added later if a
templated parser is wanted.

## What follows

One item per pick, modelling it in krrood and scoring it as stated above, and one report of what
krrood handles, works around or lacks, with each gap filed on
`cram2/cognitive_robot_abstract_machine`.

## Sources

- SARA: <https://nlp.jhu.edu/law/sara/>, archive `sara.tar.gz` (SHA-256 begins `e4f1b845016fc38b`);
  scripts at <https://github.com/SgfdDttt/sara> `cfc8d15ee487`; paper
  <https://arxiv.org/abs/2005.05257>.
- Catala examples: <https://github.com/CatalaLang/catala-examples> `9e251b932288`; paper
  <https://arxiv.org/abs/2103.03198>.
- OpenFisca France: <https://github.com/openfisca/openfisca-france> `be579829102c`.
- LegalBench: <https://github.com/HazyResearch/legalbench> `b46bf4ffae90`; test-split sizes from
  <https://huggingface.co/datasets/nguha/legalbench>.
- COLIEE 2026: <https://coliee.org/COLIEE2026/application>,
  <https://coliee.org/COLIEE2026/corpus/task3and4>.
- DMN TCK: <https://github.com/dmn-tck/tck> `5cd912f28183`.
- PROLEG: Satoh's overview, <https://prologyear.logicprogramming.org/docs/PROLEG_KenSatoh.pdf>.
