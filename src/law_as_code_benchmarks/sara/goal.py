"""
The goals of SARA's test directives: a provision's predicate, a conjunction of goals, or
one of the few utilities a test asks about the bindings of the goals before it.
"""

from __future__ import annotations

import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass

from krrood.ormatic.utils import classproperty
from krrood.utils import recursive_subclasses

from law_as_code_benchmarks.sara.case import GoalFunctor
from law_as_code_benchmarks.sara.case_reader import WorldReader
from law_as_code_benchmarks.sara.domain import World
from law_as_code_benchmarks.sara.prolog_term import CompoundTerm, PrologText
from law_as_code_benchmarks.sara.provision import Bindings, Provision

# %% goals


@dataclass
class Goal(ABC):
    """
    A goal of a test directive, solved over the circumstances of a case.
    """

    @abstractmethod
    def solutions(self, world: World, bindings: Bindings) -> list[Bindings]:
        """:return: Each way *bindings* extends to a solution of the goal about *world*."""

    def holds(self, world: World) -> bool:
        """:return: Whether the goal has a solution about *world*."""
        return bool(self.solutions(world, Bindings()))

    @classmethod
    def from_term(cls, term: CompoundTerm) -> Goal | None:
        """:return: The goal *term* states; None where it asks about a provision that is not modelled."""
        if term.functor == GoalFunctor.CONJUNCTION:
            left, right = (cls.from_term(argument) for argument in term.arguments)
            return None if left is None or right is None else Conjunction(left, right)
        for utility in recursive_subclasses(UtilityGoal):
            if utility.functor == term.functor:
                return utility(term=term)
        provision = Provision.modelling(term.functor)
        return (
            None if provision is None else ProvisionGoal(term=term, provision=provision)
        )


@dataclass
class ProvisionGoal(Goal):
    """
    A goal naming the predicate of a modelled provision.
    """

    term: CompoundTerm
    """
    The goal.
    """

    provision: type[Provision]
    """
    The provision its predicate asks.
    """

    def solutions(self, world: World, bindings: Bindings) -> list[Bindings]:
        return self.provision.from_goal(self.term, world).solutions(self.term, bindings)


@dataclass
class Conjunction(Goal):
    """
    Two goals that hold together, the second under the bindings of the first.
    """

    left: Goal
    """
    The goal solved first.
    """

    right: Goal
    """
    The goal solved under each solution of :attr:`left`.
    """

    def solutions(self, world: World, bindings: Bindings) -> list[Bindings]:
        return [
            solution
            for left_solution in self.left.solutions(world, bindings)
            for solution in self.right.solutions(world, left_solution)
        ]


# %% utilities


@dataclass
class UtilityGoal(Goal, ABC):
    """
    A goal of Prolog or of SARA's utilities, about the bindings of the goals before it.
    """

    term: CompoundTerm
    """
    The goal.
    """

    @classproperty
    @abstractmethod
    def functor(cls) -> GoalFunctor:
        """
        The functor the goal is asked by.
        """


@dataclass
class UnboundTest(UtilityGoal):
    """
    ``var(X)``: *X* is bound to an argument a conclusion leaves open.
    """

    @classproperty
    def functor(cls) -> GoalFunctor:
        """
        :attr:`GoalFunctor.UNBOUND`.
        """
        return GoalFunctor.UNBOUND

    def solutions(self, world: World, bindings: Bindings) -> list[Bindings]:
        return [bindings] if bindings.resolve(self.term.arguments[0]) is None else []


@dataclass
class FirstDayOfYear(UtilityGoal):
    """
    ``first_day_year(Year, Day)``: *Day* is January 1 of *Year*, as a ``YYYY-MM-DD``
    string.
    """

    @classproperty
    def functor(cls) -> GoalFunctor:
        """
        :attr:`GoalFunctor.FIRST_DAY_OF_YEAR`.
        """
        return GoalFunctor.FIRST_DAY_OF_YEAR

    def solutions(self, world: World, bindings: Bindings) -> list[Bindings]:
        year, day = self.term.arguments
        first_day = PrologText(datetime.date(bindings.resolve(year), 1, 1).isoformat())
        solution = bindings.unify(day, first_day)
        return [] if solution is None else [solution]


@dataclass
class DayOrder(UtilityGoal):
    """
    ``is_before(Day1, Day2)``: neither day is open and *Day1* is not after *Day2*.
    """

    @classproperty
    def functor(cls) -> GoalFunctor:
        """
        :attr:`GoalFunctor.DAY_ORDER`.
        """
        return GoalFunctor.DAY_ORDER

    def solutions(self, world: World, bindings: Bindings) -> list[Bindings]:
        first, second = (bindings.resolve(day) for day in self.term.arguments)
        if first is None or second is None:
            return []
        return [bindings] if WorldReader.date(first) <= WorldReader.date(second) else []
