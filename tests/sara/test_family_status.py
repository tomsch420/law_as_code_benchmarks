"""
Tests of family status, §§ `7703 <https://www.law.cornell.edu/uscode/text/26/7703>`__, `152 <https://www.law.cornell.edu/uscode/text/26/152>`__, `151 <https://www.law.cornell.edu/uscode/text/26/151>`__ and `2 <https://www.law.cornell.edu/uscode/text/26/2>`__, on the choices the model makes
where SARA's program or its cases leave one.
"""

from __future__ import annotations

import datetime

from law_as_code_benchmarks.sara.domain import (
    CalendarYear,
    Country,
    Household,
    Income,
    JointReturn,
    Kinship,
    Marriage,
    NonresidentAlienStatus,
    Party,
    Payment,
    Period,
    World,
)
from law_as_code_benchmarks.sara.family_status import (
    AgeRequirementTest,
    GrossIncomeOfParty,
    HouseholdMaintenanceTest,
    JointFilingTest,
    SpousesWithoutNonresidentAlienTest,
)
from law_as_code_benchmarks.sara.family_status_conclusions import MarriedIndividual
from law_as_code_benchmarks.sara.prolog_term import CompoundTerm

# %% a world of one family


def world_of_alice_and_bob() -> World:
    """:return: Alice and Bob, married since 2010, the calendar year 2018 considered."""
    alice, bob = Party(name="alice"), Party(name="bob")
    return World(
        united_states=Country(name="usa"),
        parties=[alice, bob],
        marriages=[
            Marriage(
                name="alice_and_bob",
                spouses=[alice, bob],
                period=Period(start=datetime.date(2010, 6, 1)),
            )
        ],
        calendar_years=[CalendarYear(number=2018)],
    )


def goal(functor: str, *arguments: object) -> CompoundTerm:
    """:return: The goal of *functor* over *arguments*."""
    return CompoundTerm(functor=functor, arguments=arguments)


# %% marital status


def test_spouses_making_a_joint_return_for_the_year_file_jointly() -> None:
    """
    A joint return of both spouses for the whole year makes each a joint filer.
    """
    world = world_of_alice_and_bob()
    world.joint_returns = [
        JointReturn(
            name="return_2018",
            filers=list(world.parties),
            period=Period(
                start=datetime.date(2018, 1, 1), end=datetime.date(2018, 12, 31)
            ),
        )
    ]
    assert JointFilingTest(world=world).holds(
        goal(JointFilingTest.predicate, "alice", "return_2018", "bob", 2018)
    )


def test_spouses_stated_married_making_a_joint_return_file_jointly() -> None:
    """
    Spouses a case states married under § 7703, with no marriage of their own, file
    jointly when they make a joint return for the year, as in SARA's program.
    """
    alice, bob = Party(name="alice"), Party(name="bob")
    world = World(
        united_states=Country(name="usa"),
        parties=[alice, bob],
        stated_conclusions=[
            MarriedIndividual(
                person=alice,
                spouse=bob,
                marriage=Marriage(name="unnamed", spouses=[alice, bob]),
                year=2018,
            )
        ],
        joint_returns=[
            JointReturn(
                name="return_2018",
                filers=[alice, bob],
                period=Period(
                    start=datetime.date(2018, 1, 1), end=datetime.date(2018, 12, 31)
                ),
            )
        ],
        calendar_years=[CalendarYear(number=2018)],
    )
    assert JointFilingTest(world=world).holds(
        goal(JointFilingTest.predicate, "alice", "return_2018", "bob", 2018)
    )


def test_paying_exactly_half_the_upkeep_maintains_a_household() -> None:
    """
    Half the cost of a household is enough, as SARA's program compares, though the
    statute asks for over half.
    """
    world = world_of_alice_and_bob()
    alice, bob = world.parties
    home = Household(name="home")
    world.payments = [
        Payment(
            name=f"upkeep_by_{payer.name}",
            payer=payer,
            recipient=None,
            amount=50,
            day=datetime.date(2018, 3, 1),
            household_maintained=home,
        )
        for payer in (alice, bob)
    ]
    assert HouseholdMaintenanceTest(world=world).holds(
        goal(HouseholdMaintenanceTest.predicate, "alice", "home", None, 2018)
    )


# %% dependents


def test_the_first_day_of_a_child_relation_counts_as_a_birthday() -> None:
    """
    A child stated to be a son since 2000, with no stated birth, is less than 25 years
    old in 2018 and younger than their parent, as SARA counts.
    """
    world = world_of_alice_and_bob()
    alice, _ = world.parties
    charlie = Party(name="charlie")
    world.parties.append(charlie)
    world.kinships = [
        Kinship(
            parent=alice,
            child=charlie,
            period=Period(start=datetime.date(2000, 10, 9)),
        )
    ]
    assert AgeRequirementTest(world=world).holds(
        goal(AgeRequirementTest.predicate, "charlie", "alice", 2018)
    )


# %% surviving spouse


def test_only_spouses_are_asked_whether_they_could_have_filed_jointly() -> None:
    """
    With the spouse left open, a taxpayer whose only spouse is a nonresident alien could
    not have made a joint return.
    """
    world = world_of_alice_and_bob()
    alice, _ = world.parties
    world.nonresident_alien_statuses = [
        NonresidentAlienStatus(
            person=alice, period=Period(start=datetime.date(1990, 3, 4))
        )
    ]
    assert not SpousesWithoutNonresidentAlienTest(world=world).holds(
        goal(SpousesWithoutNonresidentAlienTest.predicate, "bob", None, 2018)
    )


# %% conclusions drawn once per case


def test_a_provision_asked_again_about_a_case_draws_no_new_conclusions() -> None:
    """
    A provision asked twice about the same case gives the conclusions it drew first.
    """
    world = world_of_alice_and_bob()
    first = SpousesWithoutNonresidentAlienTest(world=world).conclusions
    assert SpousesWithoutNonresidentAlienTest(world=world).conclusions is first


def test_a_calendar_year_asked_about_makes_provisions_draw_conclusions_for_it_alone() -> (
    None
):
    """
    Asking about a calendar year makes a provision draw its conclusions again, for the
    years asked about only.
    """
    world = world_of_alice_and_bob()
    SpousesWithoutNonresidentAlienTest(world=world).conclusions
    world.include_calendar_year(2019)
    assert {
        conclusion.year
        for conclusion in SpousesWithoutNonresidentAlienTest(world=world).conclusions
    } == {2019}


# %% gross income


def test_spouses_filing_jointly_each_have_both_incomes_as_gross_income() -> None:
    """
    The gross income of a spouse making a joint return is their income and their
    spouse's together.
    """
    world = world_of_alice_and_bob()
    alice, bob = world.parties
    day = datetime.date(2018, 6, 1)
    world.incomes = [
        Income(earning_party=alice, amount=100, day=day),
        Income(earning_party=bob, amount=50, day=day),
    ]
    world.joint_returns = [
        JointReturn(
            name="return_2018",
            filers=[alice, bob],
            period=Period(
                start=datetime.date(2018, 1, 1), end=datetime.date(2018, 12, 31)
            ),
        )
    ]
    assert GrossIncomeOfParty(world=world).holds(
        goal(GrossIncomeOfParty.predicate, "alice", 2018, 150)
    )
