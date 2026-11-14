"""
Tests of provisions drawing their conclusions about a case once.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from krrood.entity_query_language.factories import an, entity, variable
from krrood.entity_query_language.query.query import Query

from law_as_code_benchmarks.law.provision import AssessedCase, Conclusion, Provision

# %% a provision concluding what its case lists


@dataclass(eq=False)
class ListedFact(Conclusion):
    """A conclusion the case lists itself."""

    text: str
    """What the fact says."""


@dataclass(eq=False)
class CaseListingFacts(AssessedCase):
    """A case listing the facts concluded about it."""

    facts: list[ListedFact] = field(default_factory=list)
    """The facts."""


@dataclass
class ListedFactsProvision(Provision[ListedFact]):
    """A provision concluding each fact its case lists."""

    case: CaseListingFacts
    """The case assessed."""

    @property
    def assessed_case(self) -> AssessedCase:
        return self.case

    def query(self) -> Query:
        return an(entity(variable(ListedFact, domain=self.case.facts)))


def case_with_one_fact() -> CaseListingFacts:
    """:return: A case listing one fact."""
    return CaseListingFacts(facts=[ListedFact(text="born")])


# %% drawing once


def test_a_provision_concludes_what_its_query_infers() -> None:
    """The conclusions are the query's results."""
    case = case_with_one_fact()
    assert ListedFactsProvision(case=case).conclusions == case.facts


def test_the_conclusions_are_drawn_once_per_case() -> None:
    """Another provision of the same class finds them kept in the case."""
    case = case_with_one_fact()
    drawn = ListedFactsProvision(case=case).conclusions
    case.facts.append(ListedFact(text="married"))
    assert ListedFactsProvision(case=case).conclusions == drawn


def test_the_conclusions_are_kept_under_the_provisions_key() -> None:
    """The case keeps them under the provision's class."""
    case = case_with_one_fact()
    provision = ListedFactsProvision(case=case)
    assert case.drawn_conclusions == {ListedFactsProvision: provision.conclusions}
