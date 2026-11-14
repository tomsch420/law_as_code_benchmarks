"""
The situation the French family benefits are computed for: a household, the children
in its charge, where it lives and on which day, and the money amounts involved.
"""

from __future__ import annotations

import calendar
import datetime
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from fractions import Fraction

from krrood.entity_query_language.predicate import symbolic_function
from krrood.symbol_graph.symbol_graph import Symbol

from law_as_code_benchmarks.law.period import Period
from law_as_code_benchmarks.law.provision import AssessedCase
from law_as_code_benchmarks.catala.exceptions import AmbiguousBirthday
from law_as_code_benchmarks.catala.money import Money

# %% dated values


@dataclass(frozen=True)
class DatedValue:
    """A value the law sets for a period, such as an amount revalued every year."""

    period: Period
    """The days the value is in force."""

    source: str
    """The text that sets the value."""

    @staticmethod
    @symbolic_function
    def is_in_force(value: DatedValue, day: datetime.date) -> bool:
        """:return: Whether *value* is in force on *day*."""
        return value.period.contains(day)

    @staticmethod
    def value_in_force(values: type[Enum], day: datetime.date) -> DatedValue | None:
        """:return: The value of the member of *values* in force on *day*; None where none is."""
        in_force = [
            member.value for member in values if member.value.period.contains(day)
        ]
        return in_force[0] if in_force else None


# %% places


class Territory(StrEnum):
    """
    Where a household lives, each spelled as Catala's ``Collectivité`` names it.
    """

    GUADELOUPE = "Guadeloupe"
    """Guadeloupe."""

    FRENCH_GUIANA = "Guyane"
    """French Guiana."""

    MARTINIQUE = "Martinique"
    """Martinique."""

    REUNION = "LaRéunion"
    """La Réunion."""

    SAINT_BARTHELEMY = "SaintBarthélemy"
    """Saint-Barthélemy."""

    SAINT_MARTIN = "SaintMartin"
    """Saint-Martin."""

    METROPOLITAN_FRANCE = "Métropole"
    """Metropolitan France."""

    SAINT_PIERRE_AND_MIQUELON = "SaintPierreEtMiquelon"
    """Saint-Pierre-et-Miquelon."""

    MAYOTTE = "Mayotte"
    """Mayotte."""


# %% children


class ChildCare(StrEnum):
    """
    Who takes care of a child, each spelled as Catala's ``PriseEnCharge`` names it.
    """

    SHARED_RESIDENCE_SHARED_ALLOWANCE = "GardeAlternéePartageAllocations"
    """The child lives with each parent in turn, and the parents share the allowances."""

    SHARED_RESIDENCE_SINGLE_RECIPIENT = "GardeAlternéeAllocataireUnique"
    """The child lives with each parent in turn, and the parents named one of them to receive the allowances."""

    EFFECTIVE_AND_PERMANENT = "EffectiveEtPermanente"
    """The household takes care of the child, effectively and permanently."""

    SOCIAL_SERVICES_PAID_TO_FAMILY = "ServicesSociauxAllocationVerséeÀLaFamille"
    """The child is entrusted to child welfare, and a judge kept the allowance with the family."""

    SOCIAL_SERVICES_PAID_TO_SERVICES = (
        "ServicesSociauxAllocationVerséeAuxServicesSociaux"
    )
    """The child is entrusted to child welfare, which receives the child's part of the allowance."""


class SchoolingStage(StrEnum):
    """
    Where a child stands to compulsory schooling, each spelled as Catala's
    ``SituationObligationScolaire`` names it.
    """

    BEFORE = "Avant"
    """Before compulsory schooling begins."""

    DURING = "Pendant"
    """During compulsory schooling."""

    AFTER = "Après"
    """After compulsory schooling ends."""


class ChargeShare(Enum):
    """
    The share of a child that counts towards a household's allowances, each worth the
    fraction it counts for.
    """

    FULL = Fraction(1)
    """The child counts in full."""

    HALF = Fraction(1, 2)
    """The child counts for half, the parents sharing the allowances."""

    NONE = Fraction(0)
    """The child counts for nothing, its part going to child welfare."""


@dataclass(eq=False)
class Child(Symbol):
    """A child in a household's charge."""

    identifier: int
    """The number the case gives the child."""

    birth_date: datetime.date
    """The day the child was born."""

    monthly_pay: Money
    """What the child earns in a month."""

    has_opened_family_allowance: bool
    """Whether the child has already given the household a right to family allowances."""

    care: ChildCare | None = None
    """Who takes care of the child; None where the case states nothing of it."""

    receives_personal_housing_aid: bool = False
    """Whether the child receives housing aid in their own name."""

    stated_schooling_stage: SchoolingStage | None = None
    """Where the case states the child stands to compulsory schooling; None where it leaves it to the birth date."""

    @staticmethod
    @symbolic_function
    def birthday(child: Child, age: int) -> datetime.date:
        """
        :return: The day *child* turns *age*, as Catala adds years to a date.
        :raises AmbiguousBirthday: Where the child was born on February 29 and the year
            the birthday falls in has none, a day Catala refuses to round.
        """
        year = child.birth_date.year + age
        if (child.birth_date.month, child.birth_date.day) == (2, 29) and not (
            calendar.isleap(year)
        ):
            raise AmbiguousBirthday(child=child, age=age)
        return child.birth_date.replace(year=year)


# %% households


@dataclass(eq=False)
class Household(Symbol, AssessedCase):
    """
    A household claiming family benefits on one day, and what the provisions concluded
    about it.
    """

    assessment_date: datetime.date
    """The day the benefits are computed for."""

    residence: Territory
    """Where the household lives."""

    children: list[Child] = field(default_factory=list)
    """The children in the household's charge."""

    resources: Money = field(default_factory=lambda: Money.zero)
    """The household's yearly resources, which set its bracket."""

    had_child_before_2012: bool = False
    """Whether the household had a child in its charge before January 1, 2012, which matters in Mayotte."""

    stated_age_limit: int | None = None
    """
    The age limit of the right to family benefits another law sets in place of that of
    R512-2, as the housing aids do; None where R512-2's holds.
    """

    @property
    def number_of_children(self) -> int:
        """How many children are in the household's charge."""
        return len(self.children)

    @staticmethod
    @symbolic_function
    def days_until(household: Household, day: datetime.date) -> int:
        """:return: The days from the assessment date of *household* to *day*, negative for a day before it."""
        return (day - household.assessment_date).days

    @property
    def oldest_child(self) -> Child | None:
        """The first of the children born on the earliest day, as Catala's epilogue picks it; None without children."""
        return min(self.children, key=lambda child: child.birth_date, default=None)
