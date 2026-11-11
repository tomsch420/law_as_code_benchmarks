"""
A provision of SARA's statutes as a krrood rule, and the conclusions it draws.

A provision is asked as SARA's Prolog program is, by a goal naming its predicate. It
holds where one of its conclusions, inferred or stated by the case, agrees with every
argument the goal binds, and binds the goal's named variables as it agrees.
"""

from __future__ import annotations

import inspect
from functools import cached_property
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum

from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty
from krrood.patterns.subclass_safe_generic import SubClassSafeGeneric
from krrood.symbol_graph.symbol_graph import Symbol
from krrood.utils import recursive_subclasses
from typing_extensions import Generic, TypeVar

from law_as_code_benchmarks.sara.domain import World
from law_as_code_benchmarks.sara.prolog_term import (
    CompoundTerm,
    PrologText,
    PrologVariable,
    Term,
)

# %% predicates


class SaraPredicate(StrEnum):
    """The predicates of SARA's Prolog program that are modelled, each named as the program names it."""

    SERVICE_FOR_UNITED_STATES_GOVERNMENT = "s3306_c_6"
    """`§ 3306(c)(6) <https://www.law.cornell.edu/uscode/text/26/3306#c_6>`__: service in the employ of the United States Government."""

    SERVICE_FOR_STATE = "s3306_c_7"
    """`§ 3306(c)(7) <https://www.law.cornell.edu/uscode/text/26/3306#c_7>`__: service in the employ of a State."""

    SERVICE_BY_HOSPITAL_PATIENT = "s3306_c_10_B"
    """`§ 3306(c)(10)(B) <https://www.law.cornell.edu/uscode/text/26/3306#c_10_B>`__: service for a hospital by a patient of that hospital."""

    SERVICE_FOR_FOREIGN_GOVERNMENT = "s3306_c_11"
    """`§ 3306(c)(11) <https://www.law.cornell.edu/uscode/text/26/3306#c_11>`__: service in the employ of a foreign government."""

    SERVICE_FOR_INTERNATIONAL_ORGANIZATION = "s3306_c_16"
    """`§ 3306(c)(16) <https://www.law.cornell.edu/uscode/text/26/3306#c_16>`__: service in the employ of an international organization."""

    SERVICE_ABROAD_FOR_AMERICAN_EMPLOYER = "s3306_c_B"
    """`§ 3306(c)(B) <https://www.law.cornell.edu/uscode/text/26/3306#c>`__: service outside the United States by a citizen for an American employer."""

    LABOR_NOT_BY_ADMITTED_ALIEN = "s3306_c_1_B"
    """`§ 3306(c)(1)(B) <https://www.law.cornell.edu/uscode/text/26/3306#c_1_B>`__: agricultural labor not performed by an alien admitted to perform it."""

    EMPLOYER_OF_AGRICULTURAL_LABOR = "s3306_c_1_A_i"
    """`§ 3306(c)(1)(A)(i) <https://www.law.cornell.edu/uscode/text/26/3306#c_1_A_i>`__: a person who paid $20,000 or more in cash for agricultural labor."""

    EMPLOYMENT = "s3306_c"
    """`§ 3306(c) <https://www.law.cornell.edu/uscode/text/26/3306#c>`__: service that is *employment*."""

    WAGES = "s3306_b"
    """`§ 3306(b) <https://www.law.cornell.edu/uscode/text/26/3306#b>`__: remuneration for employment that is *wages*."""

    DEATH_BENEFIT_PLAN = "s3306_b_2_C"
    """`§ 3306(b)(2)(C) <https://www.law.cornell.edu/uscode/text/26/3306#b_2_C>`__: a plan making provision for employees in case of death."""

    EMPLOYER = "s3306_a"
    """`§ 3306(a) <https://www.law.cornell.edu/uscode/text/26/3306#a>`__: a person who is an *employer* for a calendar year."""

    EMPLOYER_BY_WAGES = "s3306_a_1_A"
    """`§ 3306(a)(1)(A) <https://www.law.cornell.edu/uscode/text/26/3306#a_1_A>`__: a person who paid wages of $1,500 or more."""

    EMPLOYER_BY_DAYS_OF_EMPLOYMENT = "s3306_a_1_B"
    """`§ 3306(a)(1)(B) <https://www.law.cornell.edu/uscode/text/26/3306#a_1_B>`__: a person who employed someone on 10 days, each in a different week."""

    EMPLOYER_BY_AGRICULTURAL_WAGES = "s3306_a_2_A"
    """`§ 3306(a)(2)(A) <https://www.law.cornell.edu/uscode/text/26/3306#a_2_A>`__: a person who paid wages of $20,000 or more for agricultural labor."""

    EMPLOYER_OF_DOMESTIC_SERVICE = "s3306_a_3"
    """`§ 3306(a)(3) <https://www.law.cornell.edu/uscode/text/26/3306#a_3>`__: a person who paid $1,000 or more in cash for domestic service."""

    TOTAL_WAGES = "total_wages_employer"
    """The wages an employer paid in a period, each employee's capped at $7,000 by `§ 3306(b)(1) <https://www.law.cornell.edu/uscode/text/26/3306#b_1>`__."""

    EXCISE_TAX = "s3301"
    """`§ 3301 <https://www.law.cornell.edu/uscode/text/26/3301>`__: the excise tax on an employer, 6 percent of the wages paid in a calendar year."""


# %% bindings


@dataclass(frozen=True)
class Bindings:
    """The values a goal's named variables are bound to so far."""

    values: dict[str, Term] = field(default_factory=dict)
    """The value of each bound variable, by name; None for one bound to an argument a conclusion leaves open."""

    def unify(self, asked: Term, concluded: Term) -> Bindings | None:
        """
        :param asked: An argument of a goal.
        :param concluded: The argument a conclusion gives in its place.
        :return: The bindings extended so that *asked* agrees with *concluded*; None if it cannot.
        """
        if asked is None:
            return self
        if isinstance(asked, PrologVariable):
            if asked.name not in self.values:
                return Bindings(values={**self.values, asked.name: concluded})
            asked = self.values[asked.name]
        if self.text_of(asked) != self.text_of(concluded):
            return None
        return self

    def resolve(self, term: Term) -> Term:
        """:return: The value *term* is bound to, if it is a bound variable; else *term* itself."""
        if isinstance(term, PrologVariable):
            return self.values.get(term.name)
        return term

    @staticmethod
    def text_of(term: Term) -> Term:
        """:return: The characters of a Prolog string, as the domain model names things; any other term itself."""
        return term.value if isinstance(term, PrologText) else term


# %% conclusions


@dataclass(eq=False)
class SaraConclusion(Symbol, ABC):
    """What a provision concludes, for the arguments of its predicate."""

    @abstractmethod
    def prolog_arguments(self) -> tuple[Term, ...]:
        """:return: The conclusion as the arguments of the provision's predicate, in the program's order."""

    def unify(self, goal: CompoundTerm, bindings: Bindings) -> Bindings | None:
        """:return: *bindings*, extended so that the conclusion agrees with every argument of *goal*; None if it cannot."""
        arguments = self.prolog_arguments()
        if len(goal.arguments) != len(arguments):
            return None
        for asked, concluded in zip(goal.arguments, arguments):
            bindings = bindings.unify(asked, concluded)
            if bindings is None:
                return None
        return bindings


ConclusionType = TypeVar("ConclusionType", bound=SaraConclusion)


# %% provisions


@dataclass
class Provision(Generic[ConclusionType], SubClassSafeGeneric, ABC):
    """A provision of the statutes, drawing its conclusions about a case."""

    world: World
    """The circumstances of the case."""

    @classproperty
    @abstractmethod
    def predicate(cls) -> SaraPredicate:
        """The predicate of SARA's program the provision is asked by."""

    @classproperty
    def year_position(cls) -> int | None:
        """The position of the calendar year among the predicate's arguments; None where it takes none."""
        return None

    @abstractmethod
    def query(self) -> Query:
        """:return: A query inferring the provision's conclusions about the case."""

    @classmethod
    def from_goal(cls, goal: CompoundTerm, world: World) -> Provision:
        """:return: The provision about *world*, the calendar year *goal* names among the years it considers."""
        if cls.year_position is not None:
            year = goal.arguments[cls.year_position]
            if isinstance(year, int):
                world.include_calendar_year(year)
        return cls(world=world)

    @cached_property
    def conclusions(self) -> list[ConclusionType]:
        """The conclusions the provision infers, followed by those of its kind the case states."""
        conclusion_type = self.get_type_of_generic_parameter(parameter=ConclusionType)
        return self.query().tolist() + [
            conclusion
            for conclusion in self.world.stated_conclusions
            if isinstance(conclusion, conclusion_type)
        ]

    def solutions(self, goal: CompoundTerm, bindings: Bindings) -> list[Bindings]:
        """:return: The bindings each conclusion agreeing with *goal*, which names the predicate, extends *bindings* to."""
        return [
            solution
            for conclusion in self.conclusions
            if (solution := conclusion.unify(goal, bindings)) is not None
        ]

    def holds(self, goal: CompoundTerm) -> bool:
        """:return: Whether one of the provision's conclusions agrees with *goal*, which names its predicate."""
        return bool(self.solutions(goal, Bindings()))

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
