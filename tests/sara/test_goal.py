"""
Tests of solving the goals of SARA's test directives: conjunctions sharing variables,
and the utilities a test asks about their bindings.
"""

from __future__ import annotations

from law_as_code_benchmarks.sara.case import GoalFunctor, SaraCase
from law_as_code_benchmarks.sara.domain import Country, World
from law_as_code_benchmarks.sara.goal import Conjunction, Goal
from law_as_code_benchmarks.sara.prolog_term import (
    CompoundTerm,
    PrologText,
    PrologVariable,
)

# %% named variables of test goals


def test_a_conjunctive_test_goal_keeps_the_variables_its_conjuncts_share() -> None:
    """
    The conjuncts of a test goal name the variables they share alike.
    """
    goal = SaraCase.load("s152_d_2_G_pos").test.goal
    relationship, constraints = goal.arguments
    assert goal.functor == GoalFunctor.CONJUNCTION
    assert relationship.arguments[3] == constraints.arguments[0].arguments[0]
    assert relationship.arguments[3] == PrologVariable("End_relationship")


# %% conjunctions and utilities


def empty_world() -> World:
    """:return: A world of no circumstances."""
    return World(united_states=Country(name="usa"))


def first_days_of(first_year: int, second_year: int) -> CompoundTerm:
    """:return: The goal that one variable is January 1 of both *first_year* and *second_year*."""
    first_day = PrologVariable("First_day")
    return CompoundTerm(
        functor=GoalFunctor.CONJUNCTION,
        arguments=tuple(
            CompoundTerm(
                functor=GoalFunctor.FIRST_DAY_OF_YEAR, arguments=(year, first_day)
            )
            for year in (first_year, second_year)
        ),
    )


def test_a_variable_bound_once_agrees_only_with_its_value() -> None:
    """
    A variable bound to a day agrees with that day and no other.
    """
    assert Goal.from_term(first_days_of(2018, 2018)).holds(empty_world())
    assert not Goal.from_term(first_days_of(2018, 2019)).holds(empty_world())


def first_day_of_2018_compared_with(day: str) -> CompoundTerm:
    """:return: The goal that January 1, 2018 is bound to a variable and *day* is not after it."""
    first_day = PrologVariable("First_day")
    return CompoundTerm(
        functor=GoalFunctor.CONJUNCTION,
        arguments=(
            CompoundTerm(
                functor=GoalFunctor.FIRST_DAY_OF_YEAR, arguments=(2018, first_day)
            ),
            CompoundTerm(
                functor=GoalFunctor.DAY_ORDER, arguments=(PrologText(day), first_day)
            ),
        ),
    )


def test_a_conjunction_solves_its_second_goal_under_the_bindings_of_its_first() -> None:
    """
    The second goal of a conjunction sees the day the first bound.
    """
    assert Goal.from_term(first_day_of_2018_compared_with("2017-05-01")).holds(
        empty_world()
    )
    assert not Goal.from_term(first_day_of_2018_compared_with("2018-05-01")).holds(
        empty_world()
    )


def test_a_bound_variable_is_not_unbound() -> None:
    """
    ``var`` fails on a variable a goal before it bound to a day.
    """
    first_day = PrologVariable("First_day")
    goal = Goal.from_term(
        CompoundTerm(
            functor=GoalFunctor.CONJUNCTION,
            arguments=(
                CompoundTerm(
                    functor=GoalFunctor.FIRST_DAY_OF_YEAR, arguments=(2018, first_day)
                ),
                CompoundTerm(functor=GoalFunctor.UNBOUND, arguments=(first_day,)),
            ),
        )
    )
    assert isinstance(goal, Conjunction)
    assert not goal.holds(empty_world())


def test_a_conjunction_with_an_unmodelled_goal_is_not_modelled() -> None:
    """
    A conjunction one of whose goals asks about an unmodelled predicate is not modelled.
    """
    term = CompoundTerm(
        functor=GoalFunctor.CONJUNCTION,
        arguments=(
            CompoundTerm(functor="unmodelled_predicate", arguments=()),
            CompoundTerm(functor=GoalFunctor.UNBOUND, arguments=(None,)),
        ),
    )
    assert Goal.from_term(term) is None
