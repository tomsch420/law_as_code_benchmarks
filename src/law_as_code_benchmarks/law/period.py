"""
Periods of days, over which facts hold and the law sets its values.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from krrood.entity_query_language.predicate import symbolic_function

# %% periods


@dataclass(frozen=True)
class Period:
    """
    The days from a first to a last, both included, either of which may be left open.
    """

    first_day: datetime.date | None = None
    """
    The first day; None where the period has no stated beginning.
    """

    last_day: datetime.date | None = None
    """
    The last day; None where the period goes on.
    """

    def contains(self, day: datetime.date) -> bool:
        """:return: Whether *day* falls in the period, an open end bounding nothing."""
        return (self.first_day is None or self.first_day <= day) and (
            self.last_day is None or day <= self.last_day
        )

    def overlaps(self, other: Period) -> bool:
        """:return: Whether the period and *other* share a day at least."""
        return (
            self.first_day is None
            or other.last_day is None
            or self.first_day <= other.last_day
        ) and (
            other.first_day is None
            or self.last_day is None
            or other.first_day <= self.last_day
        )

    @symbolic_function
    def intersect(self, other: Period) -> Period:
        """:return: The days the period and *other* share, from the later stated first day to the earlier stated last day."""
        first_days = [
            day for day in (self.first_day, other.first_day) if day is not None
        ]
        last_days = [day for day in (self.last_day, other.last_day) if day is not None]
        return Period(
            first_day=max(first_days, default=None),
            last_day=min(last_days, default=None),
        )
