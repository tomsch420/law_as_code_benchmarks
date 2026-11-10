"""
A provision of SARA's statutes as a krrood rule, and the conclusions it draws.

A provision is asked as SARA's Prolog program is: by a goal naming its predicate, with
each argument bound or left open. It holds where one of its conclusions agrees with
every argument the goal binds.
"""

from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum

from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty
from krrood.patterns.subclass_safe_generic import SubClassSafeGeneric
from krrood.symbol_graph.symbol_graph import Symbol
from krrood.utils import recursive_subclasses
from typing_extensions import Generic, TypeVar

from law_as_code_benchmarks.sara.domain import World
from law_as_code_benchmarks.sara.prolog_term import CompoundTerm, PrologText, Term

# %% predicates


class SaraPredicate(StrEnum):
    """The predicates of SARA's Prolog program that are modelled, each named as the program names it."""

    SERVICE_FOR_UNITED_STATES_GOVERNMENT = "s3306_c_6"
    """§ 3306(c)(6): service in the employ of the United States Government."""

    SERVICE_FOR_STATE = "s3306_c_7"
    """§ 3306(c)(7): service in the employ of a State."""

    SERVICE_BY_HOSPITAL_PATIENT = "s3306_c_10_B"
    """§ 3306(c)(10)(B): service for a hospital by a patient of that hospital."""

    SERVICE_FOR_FOREIGN_GOVERNMENT = "s3306_c_11"
    """§ 3306(c)(11): service in the employ of a foreign government."""

    SERVICE_FOR_INTERNATIONAL_ORGANIZATION = "s3306_c_16"
    """§ 3306(c)(16): service in the employ of an international organization."""

    SERVICE_ABROAD_FOR_AMERICAN_EMPLOYER = "s3306_c_B"
    """§ 3306(c)(B): service outside the United States by a citizen for an American employer."""

    LABOR_NOT_BY_ADMITTED_ALIEN = "s3306_c_1_B"
    """§ 3306(c)(1)(B): agricultural labor not performed by an alien admitted to perform it."""


# %% conclusions


@dataclass(eq=False)
class SaraConclusion(Symbol, ABC):
    """What a provision concludes, for the arguments of its predicate."""

    @abstractmethod
    def prolog_arguments(self) -> tuple[Term, ...]:
        """:return: The conclusion as the arguments of the provision's predicate, in the program's order."""

    def answers(self, goal: CompoundTerm) -> bool:
        """:return: Whether the conclusion agrees with every argument *goal* binds."""
        arguments = self.prolog_arguments()
        return len(goal.arguments) == len(arguments) and all(
            asked is None or self.text_of(asked) == self.text_of(concluded)
            for asked, concluded in zip(goal.arguments, arguments)
        )

    @staticmethod
    def text_of(term: Term) -> Term:
        """:return: The characters of a Prolog string, as the domain model names things; any other term itself."""
        return term.value if isinstance(term, PrologText) else term


ConclusionType = TypeVar("ConclusionType", bound=SaraConclusion)


# %% provisions


@dataclass
class Provision(Generic[ConclusionType], SubClassSafeGeneric, ABC):
    """A provision of the statutes, asked about a case by a goal."""

    world: World
    """The circumstances of the case."""

    goal: CompoundTerm
    """The goal the provision is asked, naming its predicate."""

    @classproperty
    @abstractmethod
    def predicate(cls) -> SaraPredicate:
        """The predicate of SARA's program the provision is asked by."""

    @abstractmethod
    def query(self) -> Query:
        """:return: A query inferring the provision's conclusions about the case."""

    def holds(self) -> bool:
        """:return: Whether one of the provision's conclusions answers :attr:`goal`."""
        return any(
            conclusion.answers(self.goal) for conclusion in self.query().tolist()
        )

    @classmethod
    def modelling(cls, predicate_name: str) -> type[Provision] | None:
        """:return: The provision asked by the predicate named *predicate_name*; None if none is modelled."""
        for provision in recursive_subclasses(cls):
            if (
                not inspect.isabstract(provision)
                and provision.predicate == predicate_name
            ):
                return provision
        return None
