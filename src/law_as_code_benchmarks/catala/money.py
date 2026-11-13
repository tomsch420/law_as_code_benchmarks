"""
Money as Catala computes with it: whole cents, rounded to the cent after every
multiplication.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

from krrood.ormatic.utils import classproperty

# %% money


@dataclass(frozen=True, order=True)
class Money:
    """
    An amount of money, kept in whole cents as Catala's ``money``, whatever the
    currency.
    """

    cents: int
    """
    The amount in cents.
    """

    @classproperty
    def zero(cls) -> Money:
        """
        No money.
        """
        return cls(cents=0)

    @classmethod
    def from_euros(cls, euros: Decimal | int) -> Money:
        """:return: *euros*, or another currency's units, which hold whole cents, as money."""
        return cls(cents=int(Decimal(euros) * 100))

    def __add__(self, other: Money) -> Money:
        """:return: The sum of both amounts."""
        return Money(cents=self.cents + other.cents)

    def __sub__(self, other: Money) -> Money:
        """:return: The amount less *other*."""
        return Money(cents=self.cents - other.cents)

    def __mul__(self, factor: Fraction | int) -> Money:
        """:return: The amount times *factor*, rounded to the cent, halves away from zero, as Catala rounds."""
        exact = self.cents * Fraction(factor)
        rounded = math.floor(abs(exact) + Fraction(1, 2))
        return Money(cents=rounded if exact >= 0 else -rounded)

    def __truediv__(self, other: Money) -> Fraction:
        """:return: The exact ratio of the amount to *other*, as Catala divides money by money."""
        return Fraction(self.cents, other.cents)

    def __rmul__(self, factor: Fraction | int) -> Money:
        """:return: The amount times *factor*, as :meth:`__mul__` rounds it."""
        return self * factor

    def __radd__(self, other: Money | int) -> Money:
        """:return: The amount added to *other*, which :func:`sum` starts at 0."""
        return self if other == 0 else self + other

    def __str__(self) -> str:
        """:return: The amount in units of its currency, with two decimals."""
        return f"{Decimal(self.cents) / 100:.2f}"
