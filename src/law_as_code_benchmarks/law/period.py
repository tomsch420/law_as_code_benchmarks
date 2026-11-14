"""
Periods of days, over which facts hold and the law sets its values.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from krrood.bounds import Bounds
from krrood.entity_query_language.predicate import symbolic_function

# %% periods


@dataclass(kw_only=True)
class Period(Bounds[datetime.date | None]):
    """
    The days from a first to a last, both included, either of which may be left open.
    """

    lower: datetime.date | None = None
    """
    The first day; None where the period has no stated beginning.
    """

    upper: datetime.date | None = None
    """
    The last day; None where the period goes on.
    """

    def contains(self, day: datetime.date) -> bool:
        """:return: Whether *day* falls in the period, an open end bounding nothing."""
        return (self.lower is None or self.lower <= day) and (
            self.upper is None or day <= self.upper
        )

    def overlaps(self, other: Period) -> bool:
        """:return: Whether the period and *other* share a day at least."""
        return (
            self.lower is None or other.upper is None or self.lower <= other.upper
        ) and (other.lower is None or self.upper is None or other.lower <= self.upper)

    @symbolic_function
    def intersect(self, other: Period) -> Period:
        """:return: The days the period and *other* share, from the later stated first day to the earlier stated last day."""
        first_days = [day for day in (self.lower, other.lower) if day is not None]
        last_days = [day for day in (self.upper, other.upper) if day is not None]
        return Period(
            lower=max(first_days, default=None),
            upper=min(last_days, default=None),
        )
