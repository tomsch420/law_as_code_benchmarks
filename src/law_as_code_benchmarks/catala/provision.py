"""
The rule trees of Catala's provisions, and the provisions of the family benefits.

A provision states one variable of Catala's scopes, a default with exceptions as a rule
tree: rules of equal standing are alternatives, each tried where those before it fail,
an exception to one rule is a refinement of it, and Catala's default comes last.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass

from krrood.entity_query_language.factories import (
    add,
    alternative,
    an,
    entity,
    variable,
)
from krrood.entity_query_language.query.query import Query
from typing_extensions import Any, TypeVar

from law_as_code_benchmarks.catala.domain import DatedValue, Household
from law_as_code_benchmarks.law.provision import (
    AssessedCase,
    ConclusionType,
    Provision,
)

DatedValueType = TypeVar("DatedValueType", bound=DatedValue)


# %% rule chains


@dataclass(frozen=True)
class RuleBranch:
    """
    A rule of an else-if chain: its conditions and the inference it adds.
    """

    conditions: tuple[Any, ...]
    """
    The conditions, all of which must hold; none for the chain's default.
    """

    inferred: Any
    """
    The inference the rule adds.
    """


@dataclass(frozen=True)
class RuleChain:
    """
    An else-if chain of rules of equal standing, each tried where those before it fail,
    whose rules are chosen as the chain is built: a rule whose amounts are not in force
    is left out, krrood refusing a condition that is a plain truth value.
    """

    conclusion: Any
    """
    The deduced variable the rules conclude.
    """

    branches: list[RuleBranch]
    """
    The rules, in order, the default last.
    """

    def query(self) -> Query:
        """:return: The query of the chain; a plain inference where only the default is left."""
        first, *others = self.branches
        if not first.conditions:
            return an(entity(first.inferred))
        query = an(entity(self.conclusion).where(*first.conditions))
        with query:
            add(self.conclusion, first.inferred)
            for branch in others:
                with alternative(*branch.conditions):
                    add(self.conclusion, branch.inferred)
        return query


# %% provisions


@dataclass
class FamilyBenefitsProvision(Provision[ConclusionType], ABC):
    """
    A provision of the family benefits, drawing its conclusions about a household.
    """

    household: Household
    """
    The household assessed.
    """

    @property
    def assessed_case(self) -> AssessedCase:
        return self.household

    def values_in_force(self, values: list[DatedValueType]) -> list[DatedValueType]:
        """
        :return: Those of *values* in force on the household's assessment date. A rule
            tree draws its values from these, as an alternative tried after a branch
            over values not in force would otherwise be tried once for each of them.
        """
        value = variable(DatedValue, domain=values)
        return an(
            entity(value).where(
                DatedValue.is_in_force(value, self.household.assessment_date)
            )
        ).tolist()


@dataclass
class ChildProvision(FamilyBenefitsProvision[ConclusionType], ABC):
    """
    A provision of the family benefits drawing a conclusion about each child in the
    household's charge.
    """

    @property
    def conclusions(self) -> list[ConclusionType]:
        """
        Extends :meth:`~law_as_code_benchmarks.law.provision.Provision.conclusions`:

        none for a household without children.
        """
        # krrood raises on an else-if chain over an empty domain:
        # https://github.com/cram2/cognitive_robot_abstract_machine/issues/952
        if not self.household.children:
            return []
        return super().conclusions
