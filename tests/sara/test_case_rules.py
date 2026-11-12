"""
Tests of expanding the rules of SARA's cases into the facts they state.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from law_as_code_benchmarks.sara.case_rules import (
    FactExpansion,
    FactOnDaysOfPeriod,
    FactsAboutNamedEvents,
    FactsAboutSeries,
    RosterOfEvents,
    SeriesOfEvents,
)
from law_as_code_benchmarks.sara.exceptions import UnrecognizedCaseRule
from law_as_code_benchmarks.sara.prolog_term import (
    CompoundTerm,
    PrologReader,
    PrologText,
)

# %% expanding a case file


def expansion(file_name: str) -> FactExpansion:
    """:return: The expansion of the clauses of :file:`case_files/{file_name}`."""
    clauses = PrologReader().read_clauses(
        (Path(__file__).parent / "case_files" / file_name).read_text()
    )
    return FactExpansion(clauses=clauses)


def facts_of(expansion: FactExpansion, functor: str) -> list[tuple]:
    """:return: The arguments of the facts of *functor* the expansion states, in order."""
    return [fact.arguments for fact in expansion.facts if fact.functor == functor]


# %% kinds of rules


def test_a_yearly_series_names_an_event_for_each_year_with_its_own_first_day() -> None:
    """
    A series over years names one event a year, starting on January 1 except in the year
    the case states another day for.
    """
    upkeep = expansion("yearly_upkeep.pl")
    assert [type(rule) for rule in upkeep.rules] == [
        SeriesOfEvents,
        FactsAboutSeries,
        FactsAboutSeries,
    ]
    assert facts_of(upkeep, "start_") == [
        ("bob_maintains_household_2017", PrologText("2017-09-16")),
        ("bob_maintains_household_2018", PrologText("2018-01-01")),
        ("bob_maintains_household_2019", PrologText("2019-01-01")),
    ]


def test_a_roster_names_an_event_for_each_person_working_each_day() -> None:
    """
    A roster names one event for each listed person on each listed day, and a rule about
    its events can spell further names from theirs.
    """
    roster = expansion("farm_work_roster.pl")
    assert isinstance(roster.rules[0], RosterOfEvents)
    assert facts_of(roster, "payment_") == [
        ("alice_employer_2017-01-24_bob_payment",),
        ("alice_employer_2017-01-24_cameron_payment",),
        ("alice_employer_2017-02-04_dan_payment",),
    ]


def test_facts_about_named_events_hold_for_each_name_of_the_pattern() -> None:
    """
    A rule splitting an event's name holds for each event the case's other facts name
    whose name has the parts it requires, and pairs names agreeing in their parts.
    """
    workforce = expansion("numbered_workforce.pl")
    assert isinstance(workforce.rules[-1], FactsAboutNamedEvents)
    assert facts_of(workforce, "agent_") == [
        ("workforalice_2015_1", "employee_2015_1"),
        ("workforalice_2015_2", "employee_2015_2"),
    ]
    assert facts_of(workforce, "purpose_") == [
        ("payment_2015_1", "workforalice_2015_1"),
        ("payment_2015_2", "workforalice_2015_2"),
    ]


def test_a_fact_on_the_days_of_a_period_is_stated_with_the_day_left_open() -> None:
    """
    A fact holding on the days of a period, or with the day left open, is stated once,
    the day left open.
    """
    employment = expansion("employment_over_period.pl")
    assert isinstance(employment.rules[0], FactOnDaysOfPeriod)
    assert employment.facts == [
        CompoundTerm(
            functor="s3306_c",
            arguments=("alice_employer", "alice", "bob", None, None),
        )
    ]


def test_a_rule_of_no_known_shape_cannot_be_expanded() -> None:
    """
    A rule in a shape no kind of rule has stops the expansion.
    """
    with pytest.raises(UnrecognizedCaseRule):
        expansion("unrecognized_rule.pl").facts
