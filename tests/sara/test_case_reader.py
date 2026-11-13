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
from law_as_code_benchmarks.sara.provision import SaraPredicate

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


def test_a_fact_about_every_event_holds_for_each_service() -> None:
    """
    A fact leaving its event open, such as ``purpose_(_,"domestic service")``, holds for
    every service, as in Prolog.
    """
    service = (
        WorldReader.from_facts(
            service_facts("alice")
            + [fact(Relation.PURPOSE, None, PrologText(SaraName.DOMESTIC_SERVICE))]
        )
        .read()
        .services[0]
    )
    assert service.kinds == {LaborKind.AGRICULTURAL_LABOR, LaborKind.DOMESTIC_SERVICE}


def test_a_service_stated_as_employment_of_several_employees_is_one_for_each() -> None:
    """
    A service name a case states employment of several employees under names a service
    of each of them.
    """
    world = WorldReader.from_facts(
        [
            fact(
                SaraPredicate.EMPLOYMENT,
                "harvest",
                "alice",
                employee,
                PrologText("2017-01-24"),
                None,
            )
            for employee in ("bob", "carol")
        ]
    ).read()
    assert [
        (conclusion.service.name, conclusion.service.employee.name)
        for conclusion in world.stated_conclusions
    ] == [("harvest", "bob"), ("harvest", "carol")]


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


# %% families and homes


def home_facts() -> list[CompoundTerm]:
    """:return: The facts of Alice and Charlie living in Alice's house since 2017, and Alice paying for its upkeep."""
    return [
        fact(EventType.RESIDENCE, "home"),
        fact(Relation.AGENT, "home", "alice"),
        fact(Relation.AGENT, "home", "charlie"),
        fact(Relation.PATIENT, "home", "alice_s_house"),
        fact(Relation.START, "home", PrologText("2017-09-16")),
        fact(EventType.PAYMENT, "upkeep"),
        fact(Relation.AGENT, "upkeep", "alice"),
        fact(Relation.AMOUNT, "upkeep", 40),
        fact(Relation.PURPOSE, "upkeep", "home"),
        fact(Relation.START, "upkeep", PrologText("2018-01-01")),
    ]


def test_a_residence_reads_its_residents_household_and_days() -> None:
    """
    A residence's facts become one residence of its residents in its household, from its
    start on.
    """
    residence = WorldReader.from_facts(home_facts()).read().residences[0]
    assert [resident.name for resident in residence.residents] == ["alice", "charlie"]
    assert residence.household.name == "alice_s_house"
    assert (residence.period.first_day, residence.period.last_day) == (
        datetime.date(2017, 9, 16),
        None,
    )


def test_a_payment_for_a_residence_maintains_its_household() -> None:
    """
    A payment whose purpose is a residence maintains the residence's household.
    """
    world = WorldReader.from_facts(home_facts()).read()
    assert world.payments[0].household_maintained is world.residences[0].household


def test_a_brother_relation_makes_its_agent_and_patient_siblings() -> None:
    """
    A brother relation makes siblings of its agent and its patient alike.
    """
    world = WorldReader.from_facts(
        [
            fact(EventType.BROTHER, "alice_and_bob"),
            fact(Relation.AGENT, "alice_and_bob", "bob"),
            fact(Relation.PATIENT, "alice_and_bob", "alice"),
        ]
    ).read()
    assert [sibling.name for sibling in world.siblinghoods[0].siblings] == [
        "bob",
        "alice",
    ]


def test_a_marriage_stated_with_two_starts_is_read_once_for_each() -> None:
    """
    A marriage the case states two starts of is read as one marriage for each start, as
    SARA's program tries each.
    """
    world = WorldReader.from_facts(
        [
            fact(EventType.MARRIAGE, "alice_and_bob"),
            fact(Relation.AGENT, "alice_and_bob", "alice"),
            fact(Relation.AGENT, "alice_and_bob", "bob"),
            fact(Relation.START, "alice_and_bob", PrologText("2017-02-03")),
            fact(Relation.START, "alice_and_bob", PrologText("2012-04-05")),
        ]
    ).read()
    assert [marriage.period.first_day for marriage in world.marriages] == [
        datetime.date(2017, 2, 3),
        datetime.date(2012, 4, 5),
    ]
