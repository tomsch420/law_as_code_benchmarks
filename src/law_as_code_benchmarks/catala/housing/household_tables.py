"""
The tables of the arrêté of September 27, 2019 that set an amount by household and
zone for home ownership and residence halls, read from the data files a script took off
Catala's ``aides_logement`` example: the monthly payment ceilings of articles 17, 18 and
33, the rent equivalence ceilings of article 27 and the rent equivalences of article 43.
"""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from functools import cache
from pathlib import Path

from krrood.entity_query_language.predicate import symbolic_function
from krrood.patterns.path_enumeration import PathEnumeration
from typing_extensions import Any

from law_as_code_benchmarks.catala.domain import DatedValue
from law_as_code_benchmarks.law.period import Period
from law_as_code_benchmarks.catala.housing.domain import (
    HousingZone,
    LoanType,
    ResidenceHallRentCategory,
)
from law_as_code_benchmarks.catala.money import Money

# %% data files


class HouseholdTableFile(PathEnumeration):
    """The data files of the tables, kept beside this module."""

    SCALES = Path(__file__).parent / "scales"
    """The directory holding them."""

    PERSONALISED_AID_PAYMENT_CEILINGS = SCALES / "apl_ownership_ceilings.json"
    """Articles 17 and 18."""

    ALLOWANCE_PAYMENT_CEILINGS = SCALES / "al_ownership_ceilings.json"
    """Article 33."""

    RESIDENCE_HALL_CEILINGS = SCALES / "residence_hall_ceilings.json"
    """Article 27."""

    RESIDENCE_HALL_RENT_EQUIVALENCES = SCALES / "residence_hall_rent_equivalences.json"
    """Article 43."""

    def read_rows(self) -> list[dict[str, Any]]:
        """:return: The rows of the file."""
        return json.loads(self.value.read_text())

    @staticmethod
    def parsed_date(text: str | None) -> datetime.date | None:
        """:return: The date *text* writes, in ISO format; None for none."""
        return None if text is None else datetime.date.fromisoformat(text)

    @staticmethod
    def assessment_period(row: dict[str, Any]) -> Period:
        """:return: The days from the row's first day of assessment to the day before its last."""
        before = HouseholdTableFile.parsed_date(row[TableKey.ASSESSED_BEFORE])
        return Period(
            lower=HouseholdTableFile.parsed_date(row[TableKey.ASSESSED_FROM]),
            upper=None if before is None else before - datetime.timedelta(days=1),
        )


class TableKey(StrEnum):
    """The keys of the data files."""

    SINGLE = "single"
    """The amount of a person alone without dependants."""

    COUPLE = "couple"
    """The amount of a couple without dependants."""

    BY_DEPENDANTS = "by_dependants"
    """The amounts of one dependant, two, and so on."""

    BEYOND_LISTED = "beyond_listed"
    """The amount further dependants are added to."""

    EACH_FURTHER_DEPENDANT = "each_further_dependant"
    """The amount added for each further dependant."""

    ZONES = "zones"
    """The tables by zone."""

    ALL_ZONES = "all"
    """The key of a table that holds in every zone."""

    ASSESSED_FROM = "assessed_from"
    """The first day of assessment a row holds from."""

    ASSESSED_BEFORE = "assessed_before"
    """The day of assessment a row holds until, excluded."""

    SIGNED_FROM = "signed_from"
    """The first signature date a row holds from."""

    SIGNED_BEFORE = "signed_before"
    """The signature date a row holds until, excluded."""

    SIGNED_UNTIL = "signed_until"
    """The signature date a row holds until, included."""

    BUILDING = "building"
    """The building age a row holds for."""

    LOAN_TYPES = "loan_types"
    """The loans a row holds for."""

    IN_FRANCS = "francs"
    """Whether the amounts are in francs."""

    EXCEPTION = "exception"
    """Whether a row is an exception to the others."""

    COMPUTED_FROM = "computed_from"
    """The first day the ceiling is computed for."""

    COMPUTED_BEFORE = "computed_before"
    """The day the ceiling is computed for until, excluded."""

    CATEGORY = "category"
    """The category of rent equivalence."""


# %% tables by household


@dataclass(frozen=True)
class HouseholdTable:
    """An amount of a person alone, a couple, and households of one dependant, two, and so on."""

    single: Money
    """Of a person alone without dependants."""

    couple: Money
    """Of a couple without dependants."""

    by_dependants: tuple[Money, ...]
    """Of one dependant, two, and so on."""

    beyond_listed: Money
    """
    The amount further dependants are added to, which Catala's text sets apart from the
    last amount listed and which may differ from it.
    """

    each_further_dependant: Money
    """Added for each dependant beyond those listed."""

    @classmethod
    def from_json(cls, json_table: dict[str, Any]) -> HouseholdTable:
        """:return: The table of *json_table*, in cents."""
        return cls(
            single=Money(cents=json_table[TableKey.SINGLE]),
            couple=Money(cents=json_table[TableKey.COUPLE]),
            by_dependants=tuple(
                Money(cents=cents) for cents in json_table[TableKey.BY_DEPENDANTS]
            ),
            beyond_listed=Money(cents=json_table[TableKey.BEYOND_LISTED]),
            each_further_dependant=Money(
                cents=json_table[TableKey.EACH_FURTHER_DEPENDANT]
            ),
        )

    def amount_for(self, couple: bool, dependants: int) -> Money:
        """:return: The amount of a couple or a person alone with *dependants*."""
        if dependants == 0:
            return self.couple if couple else self.single
        if dependants <= len(self.by_dependants):
            return self.by_dependants[dependants - 1]
        return self.beyond_listed + self.each_further_dependant * (
            dependants - len(self.by_dependants)
        )


@dataclass(frozen=True)
class ZoneTables:
    """A table by household for each zone, or one for every zone."""

    tables: dict[str, HouseholdTable]
    """The tables, by zone as Catala names it, or by :attr:`TableKey.ALL_ZONES`."""

    @classmethod
    def from_json(cls, json_tables: dict[str, Any]) -> ZoneTables:
        """:return: The tables of *json_tables*."""
        return cls(
            tables={
                zone: HouseholdTable.from_json(table)
                for zone, table in json_tables.items()
            }
        )

    @staticmethod
    @symbolic_function
    def amount_for(
        zones: ZoneTables,
        zone: HousingZone,
        couple: bool,
        dependants: int,
        factor: Fraction,
    ) -> Money:
        """:return: The amount of the household in *zone*, times *factor*."""
        table = zones.tables.get(TableKey.ALL_ZONES) or zones.tables[zone.value]
        return table.amount_for(couple, dependants) * factor


# %% payment ceilings


class BuildingCondition(StrEnum):
    """The building a row of articles 17 and 18 holds for, as the data files name it."""

    NEW = "Neuf"
    """A new building."""

    OLD = "Ancien"
    """An old building, improved by its occupant or not."""

    OLD_IMPROVED = "AncienAmélioré"
    """An old building improved by its occupant."""


@dataclass(frozen=True)
class PersonalisedAidPaymentCeiling:
    """A row of articles 17 and 18: the payment ceilings of a loan signed in a period, by household and zone."""

    is_exception: bool
    """Whether the row is an exception to the rows of article 18."""

    assessed_from: datetime.date
    """The first day of assessment the row holds from."""

    signed_from: datetime.date
    """The first signature date the row holds for."""

    signed_before: datetime.date | None
    """The signature date the row holds until, excluded; None where no such bound is set."""

    signed_until: datetime.date | None
    """The signature date the row holds until, included; None where no such bound is set."""

    building: BuildingCondition
    """The building the row holds for."""

    loan_types: frozenset[LoanType]
    """The loans the row holds for."""

    in_francs: bool
    """Whether the amounts are in francs."""

    zones: ZoneTables
    """The amounts."""

    @classmethod
    def from_json(cls, row: dict[str, Any]) -> PersonalisedAidPaymentCeiling:
        """:return: The row of *row*."""
        return cls(
            is_exception=row[TableKey.EXCEPTION],
            assessed_from=HouseholdTableFile.parsed_date(row[TableKey.ASSESSED_FROM]),
            signed_from=HouseholdTableFile.parsed_date(row[TableKey.SIGNED_FROM]),
            signed_before=HouseholdTableFile.parsed_date(row[TableKey.SIGNED_BEFORE]),
            signed_until=HouseholdTableFile.parsed_date(row[TableKey.SIGNED_UNTIL]),
            building=BuildingCondition(row[TableKey.BUILDING]),
            loan_types=frozenset(LoanType(loan) for loan in row[TableKey.LOAN_TYPES]),
            in_francs=row[TableKey.IN_FRANCS],
            zones=ZoneTables.from_json(row[TableKey.ZONES]),
        )

    @staticmethod
    @cache
    def rows() -> tuple[PersonalisedAidPaymentCeiling, ...]:
        """:return: Every row of articles 17 and 18."""
        return tuple(
            PersonalisedAidPaymentCeiling.from_json(row)
            for row in HouseholdTableFile.PERSONALISED_AID_PAYMENT_CEILINGS.read_rows()
        )

    def covers_signature(self, day: datetime.date) -> bool:
        """:return: Whether a loan signed on *day* falls in the row's period."""
        return (
            day >= self.signed_from
            and (self.signed_before is None or day < self.signed_before)
            and (self.signed_until is None or day <= self.signed_until)
        )


@dataclass(frozen=True)
class AllowancePaymentCeiling:
    """A row of article 33: the payment ceilings of the housing allowance for a period, by household and zone."""

    computed_from: datetime.date
    """The first day the row holds for."""

    computed_before: datetime.date | None
    """The day the row holds until, excluded; None for the last row."""

    in_francs: bool
    """Whether the amounts are in francs."""

    zones: ZoneTables
    """The amounts."""

    @classmethod
    def from_json(cls, row: dict[str, Any]) -> AllowancePaymentCeiling:
        """:return: The row of *row*."""
        return cls(
            computed_from=HouseholdTableFile.parsed_date(row[TableKey.COMPUTED_FROM]),
            computed_before=HouseholdTableFile.parsed_date(
                row[TableKey.COMPUTED_BEFORE]
            ),
            in_francs=row[TableKey.IN_FRANCS],
            zones=ZoneTables.from_json(row[TableKey.ZONES]),
        )

    @staticmethod
    @cache
    def rows() -> tuple[AllowancePaymentCeiling, ...]:
        """:return: Every row of article 33."""
        return tuple(
            AllowancePaymentCeiling.from_json(row)
            for row in HouseholdTableFile.ALLOWANCE_PAYMENT_CEILINGS.read_rows()
        )

    def covers(self, day: datetime.date) -> bool:
        """:return: Whether the row holds for *day*."""
        return day >= self.computed_from and (
            self.computed_before is None or day < self.computed_before
        )


# %% residence halls


@dataclass(frozen=True)
class ResidenceHallCeilings(DatedValue):
    """Article 27: the ceilings of the rent equivalence of a residence hall, by household and zone."""

    zones: ZoneTables
    """The ceilings."""

    @staticmethod
    @cache
    def versions() -> tuple[ResidenceHallCeilings, ...]:
        """:return: Every version of article 27 Catala's example states."""
        return tuple(
            ResidenceHallCeilings(
                period=HouseholdTableFile.assessment_period(row),
                source="Arrêté du 27 septembre 2019, article 27",
                zones=ZoneTables.from_json(row[TableKey.ZONES]),
            )
            for row in HouseholdTableFile.RESIDENCE_HALL_CEILINGS.read_rows()
        )


@dataclass(frozen=True)
class ResidenceHallRentEquivalence(DatedValue):
    """Article 43: the rent equivalence of a category of resident, of a person alone and of a couple."""

    category: ResidenceHallRentCategory
    """The category."""

    single: Money
    """Of a person alone."""

    couple: Money
    """Of a couple."""

    @staticmethod
    @cache
    def versions() -> tuple[ResidenceHallRentEquivalence, ...]:
        """:return: Every version of article 43 Catala's example states."""
        return tuple(
            ResidenceHallRentEquivalence(
                period=HouseholdTableFile.assessment_period(row),
                source="Arrêté du 27 septembre 2019, article 43",
                category=ResidenceHallRentCategory(row[TableKey.CATEGORY]),
                single=Money(cents=row[TableKey.SINGLE]),
                couple=Money(cents=row[TableKey.COUPLE]),
            )
            for row in HouseholdTableFile.RESIDENCE_HALL_RENT_EQUIVALENCES.read_rows()
        )
