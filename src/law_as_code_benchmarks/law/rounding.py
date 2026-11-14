"""
Rounding as the laws' reference implementations round: halves away from zero, as both
Catala and Prolog's ``round`` do.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction

from krrood.entity_query_language.predicate import symbolic_function

# %% rounding


@dataclass(frozen=True)
class Rounding:
    """
    Rounds exact numbers, inside a rule or out of one.
    """

    @staticmethod
    @symbolic_function
    def round_half_away_from_zero(value: Fraction, decimal_places: int = 0) -> Fraction:
        """:return: *value* rounded to *decimal_places*, a half rounded away from zero."""
        scale = 10**decimal_places
        whole = math.floor(abs(value) * scale + Fraction(1, 2))
        return Fraction(whole if value >= 0 else -whole, scale)
