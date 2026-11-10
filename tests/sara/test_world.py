"""
Tests of the world a case's facts describe.
"""

from __future__ import annotations

import datetime

from law_as_code_benchmarks.sara.prolog_term import CompoundTerm, PrologText
from law_as_code_benchmarks.sara.world import Event, EventKind, EventRole, World

# %% building the world


def test_typing_and_role_facts_describe_one_event() -> None:
    """
    A typing fact and role facts with one identifier describe one event.
    """
    world = World.from_facts(
        [
            CompoundTerm(
                functor=EventKind.SERVICE.value, arguments=("alice_employed",)
            ),
            CompoundTerm(
                functor=EventRole.AGENT.value, arguments=("alice_employed", "alice")
            ),
            CompoundTerm(
                functor=EventRole.START.value,
                arguments=("alice_employed", PrologText("2017-03-15")),
            ),
        ]
    )
    event = world.find("alice_employed")
    assert event.kinds == {EventKind.SERVICE}
    assert event.agents == ["alice"]
    assert event.start() == datetime.date(2017, 3, 15)


def test_a_fact_of_a_statute_predicate_is_a_stated_conclusion() -> None:
    """
    A fact of a statute's predicate is kept as a stated conclusion.
    """
    fact = CompoundTerm(functor="s151_b_applies", arguments=("alice", 2015))
    assert World.from_facts([fact]).stated_conclusions == [fact]


# %% dates


def test_an_event_is_ongoing_on_its_first_and_last_day() -> None:
    """
    An event is ongoing on its first and last day, and not after.
    """
    stay = Event(
        identifier="stay",
        starts=[PrologText("2017-03-15")],
        ends=[PrologText("2017-04-02")],
    )
    assert stay.is_ongoing_on(datetime.date(2017, 3, 15))
    assert stay.is_ongoing_on(datetime.date(2017, 4, 2))
    assert not stay.is_ongoing_on(datetime.date(2017, 4, 3))


def test_an_event_without_a_start_has_not_begun() -> None:
    """
    An event without a start is ongoing on no day.
    """
    assert not Event(identifier="stay").is_ongoing_on(datetime.date(2017, 3, 15))
