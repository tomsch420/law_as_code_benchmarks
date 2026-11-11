"""
Tests of the services `§ 3306(c) <https://www.law.cornell.edu/uscode/text/26/3306#c>`__ excludes from employment, on SARA's cases and on the
program's quirks.
"""

from __future__ import annotations

import pytest

from law_as_code_benchmarks.sara.case import SaraSplit
from law_as_code_benchmarks.sara.domain import (
    AmericanEmployer,
    Country,
    Party,
    Place,
    Service,
    World,
)
from law_as_code_benchmarks.sara.employment_exclusions import ServiceAbroadInclusion
from law_as_code_benchmarks.sara.prolog_term import CompoundTerm
from law_as_code_benchmarks.sara.provision import Provision, SaraPredicate
from law_as_code_benchmarks.sara.scoring import CaseResult

# %% SARA's cases


def modelled_test_cases() -> list[str]:
    """:return: The test-split cases asking about a modelled provision."""
    predicates = [predicate.value for predicate in SaraPredicate]
    return [
        identifier
        for identifier in SaraSplit.TEST.case_identifiers()
        if identifier.removesuffix("_pos").removesuffix("_neg") in predicates
    ]


def test_every_modelled_test_case_is_a_positive_or_negative_one() -> None:
    """
    SARA's test split asks each provision it tests once to hold and once to fail.
    """
    identifiers = modelled_test_cases()
    assert sorted(identifiers) == sorted(
        f"{identifier.removesuffix('_pos')}_{suffix}"
        for identifier in identifiers
        if identifier.endswith("_pos")
        for suffix in ("pos", "neg")
    )


@pytest.mark.parametrize("identifier", modelled_test_cases())
def test_a_case_is_answered_as_its_test_goal_states(
    identifier: str, swipl: str
) -> None:
    """
    Each test case about a modelled provision is answered as its test goal states.
    """
    result = CaseResult.from_identifier(identifier, swipl)
    assert result.is_modelled
    assert result.is_correct


# %% the place of service abroad


def world_of_service_abroad(place: Place) -> World:
    """:return: Bob, a citizen, working at *place* for Alice, an American employer."""
    united_states = Country(name="usa")
    alice = Party(name="alice")
    bob = Party(name="bob", citizenships=[united_states])
    return World(
        united_states=united_states,
        services=[Service(name="work", employee=bob, employer=alice, places=[place])],
        american_employers=[AmericanEmployer(role_taker=alice)],
    )


def goal_of_service_abroad() -> CompoundTerm:
    """:return: The goal asking whether the service ``work`` is service abroad."""
    return CompoundTerm(
        functor=ServiceAbroadInclusion.predicate, arguments=("work", None, None, None)
    )


def test_service_in_a_foreign_country_is_abroad() -> None:
    """
    Service at a place in a foreign country is service abroad.
    """
    world = world_of_service_abroad(
        Place(name="caracas", country=Country(name="venezuela"))
    )
    assert ServiceAbroadInclusion(world=world).holds(goal_of_service_abroad())


def test_service_at_a_place_in_no_stated_country_is_not_abroad() -> None:
    """
    Service at a place the case puts in no country is not taken to be abroad.
    """
    world = world_of_service_abroad(Place(name="somewhere"))
    assert not ServiceAbroadInclusion(world=world).holds(goal_of_service_abroad())


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
