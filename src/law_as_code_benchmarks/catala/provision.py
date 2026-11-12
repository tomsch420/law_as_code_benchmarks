"""
A provision of the family benefits as a krrood rule, and the conclusions it draws.

A provision states one variable of Catala's scopes, a default with exceptions as a rule
tree: rules of equal standing are alternatives, each tried where those before it fail,
an exception to one rule is a refinement of it, and Catala's default comes last.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from krrood.entity_query_language.factories import an, entity, variable
from krrood.entity_query_language.query.query import Query
from krrood.patterns.subclass_safe_generic import SubClassSafeGeneric
from krrood.symbol_graph.symbol_graph import Symbol
from typing_extensions import Generic, TypeVar

from law_as_code_benchmarks.catala.domain import DatedValue, Household

# %% conclusions


@dataclass(eq=False)
class FamilyBenefitsConclusion(Symbol, ABC):
    """
    What a provision of the family benefits concludes.
    """


ConclusionType = TypeVar("ConclusionType", bound=FamilyBenefitsConclusion)

DatedValueType = TypeVar("DatedValueType", bound=DatedValue)


# %% provisions


@dataclass
class Provision(Generic[ConclusionType], SubClassSafeGeneric, ABC):
    """
    A provision of the family benefits, drawing its conclusions about a household.
    """

    household: Household
    """
    The household assessed.
    """

    @abstractmethod
    def query(self) -> Query:
        """:return: A query inferring the provision's conclusions about the household."""

    @property
    def conclusions(self) -> list[ConclusionType]:
        """
        The conclusions the provision infers about the household, drawn once.
        """
        drawn = self.household.drawn_conclusions
        if type(self) not in drawn:
            drawn[type(self)] = self.query().tolist()
        return drawn[type(self)]

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
