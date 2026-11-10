"""
Tests of reading a case's facts into the domain model.
"""

from __future__ import annotations

import datetime

import pytest

from law_as_code_benchmarks.sara.case_reader import (
    EventType,
    Relation,
    SaraName,
    WorldReader,
)
from law_as_code_benchmarks.sara.domain import (
    ForeignGovernment,
    LaborKind,
    Party,
    StateGovernment,
    UnitedStatesGovernment,
)
from law_as_code_benchmarks.sara.exceptions import ConflictingFacts, MissingFact
from law_as_code_benchmarks.sara.prolog_term import CompoundTerm, PrologText

# %% facts


def fact(functor: str, *arguments: object) -> CompoundTerm:
    """:return: The fact of *functor* over *arguments*."""
    return CompoundTerm(functor=functor, arguments=arguments)


def service_facts(employer: object) -> list[CompoundTerm]:
    """:return: The facts of Bob's agricultural labor for *employer* in Caracas, Venezuela, in 2017."""
    return [
        fact(EventType.SERVICE, "work"),
        fact(Relation.AGENT, "work", "bob"),
        fact(Relation.PATIENT, "work", employer),
        fact(Relation.START, "work", PrologText("2017-02-01")),
        fact(Relation.LOCATION, "work", PrologText("caracas")),
        fact(Relation.COUNTRY, PrologText("caracas"), PrologText("venezuela")),
        fact(Relation.PURPOSE, "work", PrologText(SaraName.AGRICULTURAL_LABOR)),
    ]


# %% services


def test_a_service_reads_its_parties_day_place_and_kind() -> None:
    """
    A service's facts become one service with its employee, employer, start, place and
    kind.
    """
    service = WorldReader.from_facts(service_facts("alice")).read().services[0]
    assert (service.employee.name, service.employer.name) == ("bob", "alice")
    assert service.start == datetime.date(2017, 2, 1)
    assert [(place.name, place.country.name) for place in service.places] == [
        ("caracas", "venezuela")
    ]
    assert service.kinds == {LaborKind.AGRICULTURAL_LABOR}


def test_one_party_is_read_once() -> None:
    """
    A name stated in several facts is one party.
    """
    world = WorldReader.from_facts(
        service_facts("alice")
        + [
            fact(EventType.AMERICAN_EMPLOYER, "registration"),
            fact(Relation.AGENT, "registration", "alice"),
        ]
    ).read()
    assert world.american_employers[0].role_taker is world.services[0].employer


@pytest.mark.parametrize(
    "name, party_class",
    [
        (SaraName.UNITED_STATES_GOVERNMENT.value, UnitedStatesGovernment),
        ("state of maryland", StateGovernment),
        ("canadian government", ForeignGovernment),
        ("bertha's mussels", Party),
    ],
)
def test_a_government_is_recognized_by_its_name(
    name: str, party_class: type[Party]
) -> None:
    """
    SARA's names of governments make their parties governments of the matching kind.
    """
    employer = (
        WorldReader.from_facts(service_facts(PrologText(name)))
        .read()
        .services[0]
        .employer
    )
    assert type(employer) is party_class


def test_a_place_named_as_the_united_states_lies_in_it() -> None:
    """
    A place SARA names as the United States lies in the United States.
    """
    world = WorldReader.from_facts(
        [
            *service_facts("alice"),
            fact(Relation.LOCATION, "work", PrologText(SaraName.UNITED_STATES)),
        ]
    ).read()
    assert world.services[0].places[1].country is world.united_states


# %% facts the domain model cannot read


def test_a_service_without_an_employer_is_a_missing_fact() -> None:
    """
    A service with no employer stated cannot be read.
    """
    with pytest.raises(MissingFact):
        WorldReader.from_facts(
            [fact(EventType.SERVICE, "work"), fact(Relation.AGENT, "work", "bob")]
        ).read()


def test_two_starts_of_a_service_conflict() -> None:
    """
    A service stated to start on two days cannot be read.
    """
    with pytest.raises(ConflictingFacts):
        WorldReader.from_facts(
            [
                *service_facts("alice"),
                fact(Relation.START, "work", PrologText("2017-03-01")),
            ]
        ).read()
