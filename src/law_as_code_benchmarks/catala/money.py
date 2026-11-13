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
        """:return: The sum of both amounts; :data:`NotImplemented` for anything but money, which a symbolic amount answers."""
        if not isinstance(other, Money):
            return NotImplemented
        return Money(cents=self.cents + other.cents)

    def __sub__(self, other: Money) -> Money:
        """:return: The amount less *other*; :data:`NotImplemented` for anything but money."""
        if not isinstance(other, Money):
            return NotImplemented
        return Money(cents=self.cents - other.cents)

    def __mul__(self, factor: Fraction | int) -> Money:
        """
        :return: The amount times *factor*, rounded to the cent, halves away from zero,
            as Catala rounds; :data:`NotImplemented` for a factor that is no number.
        """
        if not isinstance(factor, (int, Fraction)):
            return NotImplemented
        exact = self.cents * Fraction(factor)
        rounded = math.floor(abs(exact) + Fraction(1, 2))
        return Money(cents=rounded if exact >= 0 else -rounded)

    @classmethod
    def from_exact_units(cls, units: Fraction) -> Money:
        """:return: *units* of the currency rounded to the cent, halves away from zero, as Catala's ``argent de`` rounds a decimal."""
        return cls(cents=1) * (units * 100)

    def rounded_to_units(self) -> Money:
        """:return: The amount rounded to whole units of its currency, halves away from zero, as Catala's ``arrondi`` rounds money."""
        units = math.floor(Fraction(abs(self.cents), 100) + Fraction(1, 2))
        return Money(cents=100 * (units if self.cents >= 0 else -units))

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
