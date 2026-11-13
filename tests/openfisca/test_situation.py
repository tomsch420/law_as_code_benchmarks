"""
Tests of mapping the situation of an OpenFisca test onto the family benefits' household.
"""

from __future__ import annotations

import datetime

import pytest

from law_as_code_benchmarks.catala.domain import ChildCare, Territory
from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.openfisca.exceptions import (
    PersonWithoutAge,
    UnexpectedOpenFiscaVariable,
)
from law_as_code_benchmarks.openfisca.situation import Situation

from .snippets import read_snippet

# %% children


def test_a_child_given_by_age_turned_it_on_the_first_day_of_the_month() -> None:
    """
    Children aged 7 and 5 in June 2013 are taken to be born on June 1, 2006 and 2008.
    """
    test = read_snippet("two_children_by_age.yaml")
    household = test.situation.to_household(test.month)
    assert [child.birth_date for child in household.children] == [
        datetime.date(2006, 6, 1),
        datetime.date(2008, 6, 1),
    ]


def test_children_given_by_birth_date_keep_it_and_a_shared_residence_shares_the_allowances() -> (
    None
):
    """
    Birth dates are read quoted or not; the child in shared residence has the parents
    share the allowances, the others are in the household's effective care.
    """
    test = read_snippet("shared_residence_with_wages.yaml")
    household = test.situation.to_household(test.month)
    assert [(child.birth_date, child.care) for child in household.children] == [
        (datetime.date(2008, 6, 15), ChildCare.EFFECTIVE_AND_PERMANENT),
        (datetime.date(2011, 2, 1), ChildCare.SHARED_RESIDENCE_SHARED_ALLOWANCE),
        (datetime.date(2015, 9, 30), ChildCare.EFFECTIVE_AND_PERMANENT),
    ]


def test_a_child_without_age_or_birth_date_is_refused() -> None:
    """
    A child of unknown age has no birth date to give the household.
    """
    test = read_snippet("child_without_age.yaml")
    with pytest.raises(PersonWithoutAge):
        test.situation.to_household(test.month)


# %% the household


def test_resources_are_the_wages_of_two_years_before_less_the_deduction() -> None:
    """
    In 2019, the 31,000 € of wages of 2017 less 10 % count, not the 5 € of 2018.
    """
    test = read_snippet("shared_residence_with_wages.yaml")
    household = test.situation.to_household(test.month)
    assert household.resources == Money.from_euros(31000) * (
        1 - Situation.professional_expenses_deduction
    )


@pytest.mark.parametrize(
    "file_name, territory",
    [
        ("two_children_by_age.yaml", Territory.METROPOLITAN_FRANCE),
        ("overseas_single_child.yaml", Situation.overseas_territory),
    ],
)
def test_a_family_overseas_lives_in_the_overseas_territory(
    file_name: str, territory: Territory
) -> None:
    """
    A family in an overseas department other than Mayotte lives where the model places
    every such family, and one without lives in metropolitan France.
    """
    test = read_snippet(file_name)
    assert test.situation.to_household(test.month).residence == territory


def test_an_input_the_reader_does_not_map_is_refused() -> None:
    """
    A disability, which the family allowances' tests never set, stops the reader.
    """
    with pytest.raises(UnexpectedOpenFiscaVariable):
        read_snippet("unknown_input.yaml")
