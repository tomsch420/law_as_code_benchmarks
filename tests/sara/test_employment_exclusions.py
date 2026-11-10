"""
Tests of the services § 3306(c) excludes from employment, on SARA's cases and on the
program's quirks.
"""

from __future__ import annotations

import pytest

from law_as_code_benchmarks.sara.case import SaraCase, SaraSplit
from law_as_code_benchmarks.sara.employment_exclusions import (
    ServiceAbroadInclusion,
    StatedName,
)
from law_as_code_benchmarks.sara.prolog_term import CompoundTerm
from law_as_code_benchmarks.sara.provision import Provision, SaraPredicate
from law_as_code_benchmarks.sara.scoring import CaseResult
from law_as_code_benchmarks.sara.world import Event, EventKind, World

# %% SARA's cases


def modelled_test_cases() -> list[str]:
    """:return: The test-split cases asking about a modelled provision."""
    predicates = [predicate.value for predicate in SaraPredicate]
    return [
        identifier
        for identifier in SaraSplit.TEST.case_identifiers()
        if identifier.removesuffix("_pos").removesuffix("_neg") in predicates
    ]


def test_every_modelled_provision_has_a_positive_and_a_negative_test_case() -> None:
    """
    SARA's test split asks each modelled provision once to hold and once to fail.
    """
    assert len(modelled_test_cases()) == 2 * len(SaraPredicate)


@pytest.mark.parametrize("identifier", modelled_test_cases())
def test_a_case_is_answered_as_its_test_goal_states(
    identifier: str, swipl: str
) -> None:
    """
    Each test case about a modelled provision is answered as its test goal states.
    """
    result = CaseResult.from_case(SaraCase.load(identifier, swipl))
    assert result.is_modelled
    assert result.is_correct


# %% the place of service abroad


def world_of_service_abroad() -> World:
    """:return: Bob working for Alice, an American employer, Bob a citizen; no place in any country."""
    world = World()
    world.events["work"] = Event(
        identifier="work", kinds={EventKind.SERVICE}, agents=["bob"], patients=["alice"]
    )
    world.events["employer"] = Event(
        identifier="employer", kinds={EventKind.AMERICAN_EMPLOYER}, agents=["alice"]
    )
    world.events["citizen"] = Event(
        identifier="citizen",
        kinds={EventKind.CITIZENSHIP},
        agents=["bob"],
        patients=[StatedName.UNITED_STATES.term()],
    )
    return world


def test_an_unbound_place_passes_where_the_case_puts_no_place_in_a_country() -> None:
    """
    As in the program, an unbound place counts as abroad where no place is put in a
    country.
    """
    goal = CompoundTerm(
        functor=ServiceAbroadInclusion.predicate, arguments=("work", None, None, None)
    )
    assert ServiceAbroadInclusion(world=world_of_service_abroad(), goal=goal).holds()


def test_a_place_in_the_united_states_is_not_abroad() -> None:
    """
    A place the case puts in the United States is not abroad.
    """
    world = world_of_service_abroad()
    world.events["baltimore"] = Event(
        identifier="baltimore", countries=[StatedName.UNITED_STATES.term()]
    )
    goal = CompoundTerm(
        functor=ServiceAbroadInclusion.predicate, arguments=("work", None, None, None)
    )
    assert not ServiceAbroadInclusion(world=world, goal=goal).holds()


# %% finding provisions


def test_every_modelled_predicate_has_its_provision() -> None:
    """
    Each modelled predicate finds the provision declaring it.
    """
    assert all(
        Provision.modelling(predicate).predicate == predicate
        for predicate in SaraPredicate
    )


def test_an_unmodelled_predicate_has_no_provision() -> None:
    """
    A predicate no provision declares finds none.
    """
    assert Provision.modelling("s151_a") is None
