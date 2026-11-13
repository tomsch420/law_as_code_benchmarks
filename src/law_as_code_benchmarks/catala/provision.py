"""
A provision of a Catala example as a krrood rule, drawing conclusions about a case.

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
from typing_extensions import Generic, TypeVar

from law_as_code_benchmarks.catala.assessment import AssessedCase, CatalaConclusion
from law_as_code_benchmarks.catala.domain import DatedValue, Household

ConclusionType = TypeVar("ConclusionType", bound=CatalaConclusion)

DatedValueType = TypeVar("DatedValueType", bound=DatedValue)


# %% provisions


@dataclass
class Provision(Generic[ConclusionType], SubClassSafeGeneric, ABC):
    """
    A provision of a Catala example, drawing its conclusions about a case.
    """

    @property
    @abstractmethod
    def assessed_case(self) -> AssessedCase:
        """
        The case the provision draws its conclusions about.
        """

    @abstractmethod
    def query(self) -> Query:
        """:return: A query inferring the provision's conclusions about the case."""

    @property
    def conclusions(self) -> list[ConclusionType]:
        """
        The conclusions the provision infers about the case, drawn once.
        """
        drawn = self.assessed_case.drawn_conclusions
        if type(self) not in drawn:
            drawn[type(self)] = self.query().tolist()
        return drawn[type(self)]


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
