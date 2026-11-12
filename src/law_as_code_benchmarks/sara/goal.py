"""
The goals of SARA's test directives: a provision's predicate, a conjunction of goals, or
one of the few utilities a test asks about the bindings of the goals before it, each
asked as conditions of one EQL query.
"""

from __future__ import annotations

import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass

from krrood.entity_query_language.predicate import symbolic_function
from krrood.ormatic.utils import classproperty
from krrood.utils import recursive_subclasses

from law_as_code_benchmarks.sara.case import GoalFunctor
from law_as_code_benchmarks.sara.case_reader import WorldReader
from law_as_code_benchmarks.sara.domain import World
from law_as_code_benchmarks.sara.prolog_term import CompoundTerm, Term
from law_as_code_benchmarks.sara.provision import GoalQuery, Provision

# %% goals


@dataclass
class Goal(ABC):
    """
    A goal of a test directive, solved over the circumstances of a case.
    """

    @abstractmethod
    def constrain(self, world: World, goal_query: GoalQuery) -> None:
        """
        Adds the goal about *world* to *goal_query*, after the goals before it.
        """

    def holds(self, world: World) -> bool:
        """:return: Whether the goal has a solution about *world*."""
        goal_query = GoalQuery()
        self.constrain(world, goal_query)
        return goal_query.has_answer()

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

    def constrain(self, world: World, goal_query: GoalQuery) -> None:
        self.provision.from_goal(self.term, world).constrain(self.term, goal_query)


@dataclass
class Conjunction(Goal):
    """
    Two goals that hold together, the second seeing the variables the first binds.
    """

    left: Goal
    """
    The goal solved first.
    """

    right: Goal
    """
    The goal solved under the bindings of :attr:`left`.
    """

    def constrain(self, world: World, goal_query: GoalQuery) -> None:
        self.left.constrain(world, goal_query)
        self.right.constrain(world, goal_query)


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

    def constrain(self, world: World, goal_query: GoalQuery) -> None:
        goal_query.require(goal_query.value(self.term.arguments[0]) == None)  # noqa: E711


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

    @staticmethod
    @symbolic_function
    def first_day_text(year: int) -> str:
        """:return: January 1 of *year*, as SARA's program writes it, ``YYYY-MM-DD``."""
        return datetime.date(year, 1, 1).isoformat()

    def constrain(self, world: World, goal_query: GoalQuery) -> None:
        year, day = self.term.arguments
        goal_query.unify(day, FirstDayOfYear.first_day_text(goal_query.value(year)))


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

    @staticmethod
    @symbolic_function
    def is_in_order(first: Term, second: Term) -> bool:
        """:return: Whether neither day is open and *first* is not after *second*."""
        if first is None or second is None:
            return False
        return WorldReader.date(first) <= WorldReader.date(second)

    def constrain(self, world: World, goal_query: GoalQuery) -> None:
        first, second = (goal_query.value(day) for day in self.term.arguments)
        goal_query.require(DayOrder.is_in_order(first, second))
