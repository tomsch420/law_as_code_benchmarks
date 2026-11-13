"""
Tests of periods of days.
"""

from __future__ import annotations

import datetime

from law_as_code_benchmarks.law.period import Period

# %% containing a day


def march() -> Period:
    """:return: March 2017."""
    return Period(
        first_day=datetime.date(2017, 3, 1), last_day=datetime.date(2017, 3, 31)
    )


def test_a_period_contains_its_first_and_last_day() -> None:
    """
    Both bounds are included.
    """
    assert march().contains(datetime.date(2017, 3, 1))
    assert march().contains(datetime.date(2017, 3, 31))


def test_a_period_excludes_the_days_around_it() -> None:
    """
    The day before the first and the day after the last are outside.
    """
    assert not march().contains(datetime.date(2017, 2, 28))
    assert not march().contains(datetime.date(2017, 4, 1))


def test_an_open_period_contains_every_day() -> None:
    """
    A period without bounds bounds nothing.
    """
    assert Period().contains(datetime.date(1900, 1, 1))


# %% overlapping


def test_periods_sharing_a_day_overlap() -> None:
    """
    March overlaps a period beginning on its last day.
    """
    assert march().overlaps(Period(first_day=datetime.date(2017, 3, 31)))


def test_periods_sharing_no_day_do_not_overlap() -> None:
    """
    March does not overlap a period ending the day before it.
    """
    assert not march().overlaps(Period(last_day=datetime.date(2017, 2, 28)))


# %% intersecting


def test_the_intersection_runs_from_the_later_first_day_to_the_earlier_last_day() -> (
    None
):
    """
    Open bounds give way to stated ones.
    """
    other = Period(first_day=datetime.date(2017, 3, 15))
    assert march().intersect(other) == Period(
        first_day=datetime.date(2017, 3, 15), last_day=datetime.date(2017, 3, 31)
    )
