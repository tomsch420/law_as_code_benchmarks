# krrood on law as code: what it handles, works around and lacks

This repository models three law-as-code benchmarks in krrood:
- SARA's nine sections of the United States Internal Revenue Code;
- eleven of Catala's examples;
- OpenFisca France's family allowances.

Each model is scored against the benchmark's own reference answers. This report sums up
what that took: what krrood states directly, what needed a workaround, and what it lacks.
Every gap found is filed on
[cram2/cognitive_robot_abstract_machine](https://github.com/cram2/cognitive_robot_abstract_machine/issues).

## The scores

| Benchmark | Law | Reproduced | Cases |
|---|---|---|---|
| SARA | IRC §§ 1, 2, 63, 68, 151, 152, 3301, 3306, 7703 | 376 | 376 |
| Catala examples | family benefits, housing aids, income tax, inheritance, Polish and US tax, NSW gaming, three ASP grants | 129 | 129 |
| OpenFisca France | family allowances, 2006 to 2026 | 80 | 93 |

All 129 Catala test scopes pass. 102 of them are kept here; the 27 of `impot_revenu` are
fetched, because of their CeCILL 2.1 licence.

The 13 OpenFisca misses are not krrood's. The family benefits model follows Catala's
reading of the law, and OpenFisca reads it differently in four places: which child counts
as the oldest, the flat allowance after age 20, when amounts are rounded, and whether the
overseas single-child rate falls for higher incomes. The README has the details.

## What krrood states directly

- **Defaults with exceptions.** Catala's default logic, and the exceptions SARA's statutes
  state, become rule trees. Rules of equal standing are an else-if chain of `alternative`s
  ending in the default; an exception to one rule is a `refinement` of it. Across the
  models, 158 `alternative`s and 496 `inference`s state the law this way, provision by
  provision.
- **Provisions that build on each other.** A provision's conclusions are symbols
  (`deduced_variable`, `inference`). Another provision quantifies over them with a
  `variable` whose domain is those conclusions, so the law's own structure carries over:
  the housing aids' eligibility, for instance, uses the family benefits' right of a child.
- **Conditions over the facts.** `exists`, `not_`, `count`, `sum` and `max` state SARA's
  conditions over a case's events and persons directly: for example the days and calendar
  weeks a person was employed under § 3306, or the dependants of § 152.
- **Pattern matching.** Catala's `selon … sous forme` over an enumeration whose constructors
  carry content is a test of the value's type (`type_`) followed by conditions on its
  fields.
- **Dated amounts.** Amounts in force on a date, such as monthly bases, minimum wages and the
  arrêté's scales, are values with a period, selected by a `symbolic_function`.
- **Arithmetic on domain types.** krrood's symbolic arithmetic composes with a domain's own
  operators. Money is in cents and rounded as Catala rounds; it only has to hand an
  unknown operand back with `NotImplemented`.

## What needed a workaround

| Issue | What happens | Workaround here |
|---|---|---|
| [#952](https://github.com/cram2/cognitive_robot_abstract_machine/issues/952) | An else-if chain over an empty domain raises `StopIteration`. | A provision about each child, person or flat-rate aid concludes nothing for an empty domain without running its query (`ChildProvision`, `DependantProvision`). |
| [#964](https://github.com/cram2/cognitive_robot_abstract_machine/issues/964) | A rule tree concludes only for the first value of a variable no root condition uses. | A condition on that variable that always holds goes first in the root (the age supplement's minimum age). |
| [#970](https://github.com/cram2/cognitive_robot_abstract_machine/issues/970) | A rule tree's default fires for every binding that fails a join in the root, so one entity gets contradictory conclusions. | The join is quantified with `exists` (the housing aids' persons counted). |
| [#948](https://github.com/cram2/cognitive_robot_abstract_machine/issues/948) | An else-if chain's final `alternative` loses bindings whose earlier branches failed on a variable the root used. | Each branch puts the entity's own conditions first. |
| [#949](https://github.com/cram2/cognitive_robot_abstract_machine/issues/949) | A second `alternative` inside a `refinement` attaches to the root. | Those exceptions are a top-level else-if chain. |
| [#937](https://github.com/cram2/cognitive_robot_abstract_machine/issues/937) | A variable quantified by two `exists` in one query makes it return nothing. | One variable per `exists` (SARA). |
| [#928](https://github.com/cram2/cognitive_robot_abstract_machine/issues/928) | A variable passed as an argument to a method call arrives as a symbolic attribute. | The method becomes a `symbolic_function`, which receives values. |
| [#929](https://github.com/cram2/cognitive_robot_abstract_machine/issues/929) | A field named like a method of krrood's variables, such as `first`, resolves to the method. | The field is named otherwise (a period's first day is `lower`). |
| [#971](https://github.com/cram2/cognitive_robot_abstract_machine/issues/971) | A module-level global named `cls` that is no class breaks importing the query language. | Scripts avoid the name. |
| by design | A literal `True` or `False` is refused as a condition. | `RuleChain` builds an else-if chain from the branches that apply, leaving out those whose amounts are not in force. |

## What krrood lacks for law as code

- **Explanations that justify an answer.** A legal answer is checked by its reasons. The
  explanation of an inference names its satisfied conditions without the values they held
  for ([#943](https://github.com/cram2/cognitive_robot_abstract_machine/issues/943)), and
  leaves out a satisfied `not_(exists(...))`
  ([#944](https://github.com/cram2/cognitive_robot_abstract_machine/issues/944)).
- **Functions as values.** Several of Catala's outputs are functions: the treatment of a
  housing aid applies to whatever amount it is given. A krrood provision concludes about a
  fixed case, so each application of the function is a case of its own (`AidTreatment`),
  each step of the treatment a provision of it.
- **States of a variable.** Catala's `état` gives one variable successive definitions, each
  building on the one before. Each state is a provision here: the parts of the family
  quotient take nine.
- **Scopes calling scopes.** A Catala scope calls another and may override its context
  variables. Here the calling case builds the called one, with the overrides as fields
  defaulted to the law's own values.
- **Computations over lists.** Catala maps, filters and sums lists, distributes an amount in
  proportion with rounding to the euro, and carries deficits forward year by year. krrood
  aggregates over a variable's bindings, but a computation producing a list is plain Python
  here, kept in Catala's order of operations and rounding.
- **Exact money and decimals.** Catala's money is in cents and rounded after each
  multiplication, and its decimals are exact. The domain carries both (`Money`, `Fraction`);
  krrood only composes them.

## What the benchmarks needed besides krrood

- **Readers of the benchmarks' own files:**
  - SARA's case files and statute facts are read in Python without running Prolog.
  - Catala's test files are read in French, English or Polish, including their command-line
    result blocks, scope calls, list maps and interface scopes.
  - OpenFisca's YAML tests are read with their error margins.
- **Data taken off the sources by script:** the housing tables by household are data files.
  A script read them off Catala's archives and checked each row against the money literals
  of its definition, and the same was done for the rented scales.
- **Licences:** OpenFisca France (AGPL-3.0) and Catala's income tax (CeCILL 2.1) are fetched
  by script, never committed.
