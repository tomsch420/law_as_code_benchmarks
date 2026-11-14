"""
Tests of taxable income, §§ `63 <https://www.law.cornell.edu/uscode/text/26/63>`__ and `68 <https://www.law.cornell.edu/uscode/text/26/68>`__ and the totals of `151 <https://www.law.cornell.edu/uscode/text/26/151>`__, on the choices the model
makes where SARA's program or its cases leave one.
"""

from __future__ import annotations

import datetime

from law_as_code_benchmarks.sara.case_reader import WorldReader
from law_as_code_benchmarks.law.period import Period
from law_as_code_benchmarks.sara.domain import (
    Blindness,
    CalendarYear,
    Country,
    Income,
    ItemizedDeduction,
    Marriage,
    Party,
    World,
)
from law_as_code_benchmarks.sara.family_status_conclusions import (
    ExemptionForSpouse,
    SurvivingSpouse,
)
from law_as_code_benchmarks.sara.prolog_term import CompoundTerm
from law_as_code_benchmarks.sara.provision import SaraPredicate
from law_as_code_benchmarks.sara.taxable_income import (
    BlindCountTest,
    ItemizedDeductionLimitationTest,
)

# %% a world of one taxpayer


def world_of_alice(income: float) -> World:
    """:return: Alice, unmarried, earning *income* and deducting $60,000 in 2016."""
    alice = Party(name="alice")
    day = datetime.date(2016, 12, 31)
    return World(
        united_states=Country(name="usa"),
        parties=[alice],
        incomes=[Income(earning_party=alice, amount=income, day=day)],
        itemized_deductions=[
            ItemizedDeduction(name="gifts", claimant=alice, amount=60_000, day=day)
        ],
        calendar_years=[CalendarYear(number=2016)],
    )


def goal(functor: str, *arguments: object) -> CompoundTerm:
    """:return: The goal of *functor* over *arguments*."""
    return CompoundTerm(functor=functor, arguments=arguments)


# %% the limitation on itemized deductions


def test_itemized_deductions_are_reduced_by_the_lesser_reduction() -> None:
    """
    3 percent of an income $10,000 over the applicable amount of $250,000 is less than
    80 percent of the deductions, so it is the reduction.
    """
    world = world_of_alice(income=260_000)
    assert ItemizedDeductionLimitationTest(world=world).holds(
        goal(
            ItemizedDeductionLimitationTest.predicate,
            "alice",
            260_000,
            250_000,
            60_000,
            300,
            2016,
        )
    )


# %% additional amounts for the blind


def test_a_blind_spouse_counts_as_600_additional_amounts_as_in_sara() -> None:
    """
    SARA's program counts a spouse's blindness as 600 additional amounts, not one.
    """
    alice, bob = Party(name="alice"), Party(name="bob")
    world = World(
        united_states=Country(name="usa"),
        parties=[alice, bob],
        marriages=[
            Marriage(
                name="alice_and_bob",
                spouses=[alice, bob],
                period=Period(lower=datetime.date(2010, 1, 1)),
            )
        ],
        blindnesses=[Blindness(person=alice, start=datetime.date(2014, 2, 28))],
        stated_conclusions=[
            ExemptionForSpouse(individual=alice, taxpayer=bob, year=2017)
        ],
        calendar_years=[CalendarYear(number=2017)],
    )
    assert BlindCountTest(world=world).holds(
        goal(BlindCountTest.predicate, "bob", 2017, BlindCountTest.count_for_spouse)
    )


# %% reading stated conclusions


def test_a_stated_conclusion_leaving_a_party_open_is_read_without_one() -> None:
    """
    A stated surviving spouse whose deceased spouse the case leaves open is read with no
    spouse, not with a party named after the open argument.
    """
    world = WorldReader.from_facts(
        [goal(SaraPredicate.SURVIVING_SPOUSE, "alice", None, 2017)]
    ).read()
    [survivor] = world.stated_conclusions
    assert isinstance(survivor, SurvivingSpouse)
    assert survivor.spouse is None
    assert [party.name for party in world.parties] == ["alice"]
