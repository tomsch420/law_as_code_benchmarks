"""
Tests of the behaviour of the domain model.
"""

from __future__ import annotations

import datetime

from law_as_code_benchmarks.sara.domain import Country, HospitalStay, Party

# %% hospital stays


def stay() -> HospitalStay:
    """:return: Alice's stay at Johns Hopkins from March 15th to April 2nd, 2017."""
    return HospitalStay(
        patient=Party(name="alice"),
        hospital=Party(name="johns hopkins hospital"),
        start=datetime.date(2017, 3, 15),
        end=datetime.date(2017, 4, 2),
    )


def test_a_stay_includes_its_first_and_last_day() -> None:
    """
    A stay includes the days it begins and ends on.
    """
    assert stay().includes(datetime.date(2017, 3, 15))
    assert stay().includes(datetime.date(2017, 4, 2))


def test_a_stay_excludes_the_days_around_it() -> None:
    """
    A stay excludes the day before it and the day after it.
    """
    assert not stay().includes(datetime.date(2017, 3, 14))
    assert not stay().includes(datetime.date(2017, 4, 3))


# %% citizenship


def test_a_citizen_of_two_countries_is_a_citizen_of_another_than_either() -> None:
    """
    A dual citizen is a citizen of a country other than each of the two.
    """
    united_states, mexico = Country(name="usa"), Country(name="mexico")
    person = Party(name="bob", citizenships=[united_states, mexico])
    assert person.is_citizen_of_other_country_than(united_states)


def test_a_citizen_of_one_country_only_is_not_a_citizen_of_another() -> None:
    """
    A party holding one citizenship is a citizen of no other country.
    """
    united_states = Country(name="usa")
    assert not Party(
        name="bob", citizenships=[united_states]
    ).is_citizen_of_other_country_than(united_states)
