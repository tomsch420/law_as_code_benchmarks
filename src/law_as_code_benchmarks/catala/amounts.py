"""
The amounts and rates the family benefits are computed from, each in force for a period
and set by the text named with it: the monthly base of family allowances, the minimum
wage, the resource ceilings and the rates of Mayotte.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from law_as_code_benchmarks.catala.domain import (
    DatedValue,
    Period,
    Territory,
)
from law_as_code_benchmarks.catala.money import Money

# %% the monthly base of family allowances


@dataclass(frozen=True)
class MonthlyBase(DatedValue):
    """
    The monthly base of family allowances (*base mensuelle des allocations familiales*),
    of which `L551-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000031688371>`__
    makes every family benefit a percentage.
    """

    amount: Money
    """The monthly base."""


class MonthlyBases(Enum):
    """The monthly bases, revalued every January until 2011 and every April since 2012."""

    JANUARY_2006 = MonthlyBase(
        period=Period(datetime.date(2006, 1, 1), datetime.date(2006, 12, 31)),
        source="Décret n° 2005-1769 du 30 décembre 2005",
        amount=Money(cents=36787),
    )
    """From January 1, 2006."""

    JANUARY_2007 = MonthlyBase(
        period=Period(datetime.date(2007, 1, 1), datetime.date(2007, 12, 31)),
        source="Décret n° 2006-1754 du 23 décembre 2006",
        amount=Money(cents=37412),
    )
    """From January 1, 2007."""

    JANUARY_2008 = MonthlyBase(
        period=Period(datetime.date(2008, 1, 1), datetime.date(2008, 12, 31)),
        source="Décret n° 2007-1755 du 13 décembre 2007",
        amount=Money(cents=37786),
    )
    """From January 1, 2008."""

    JANUARY_2009 = MonthlyBase(
        period=Period(datetime.date(2009, 1, 1), datetime.date(2010, 12, 31)),
        source="Décret n° 2008-1559 du 31 décembre 2008",
        amount=Money(cents=38920),
    )
    """From January 1, 2009, not revalued in 2010."""

    JANUARY_2011 = MonthlyBase(
        period=Period(datetime.date(2011, 1, 1), datetime.date(2012, 3, 31)),
        source="Décret n° 2010-1766 du 30 décembre 2010",
        amount=Money(cents=39504),
    )
    """From January 1, 2011."""

    APRIL_2012 = MonthlyBase(
        period=Period(datetime.date(2012, 4, 1), datetime.date(2013, 3, 31)),
        source="Loi n° 2011-1906 du 21 décembre 2011, article 104",
        amount=Money(cents=39900),
    )
    """From April 1, 2012."""

    APRIL_2013 = MonthlyBase(
        period=Period(datetime.date(2013, 4, 1), datetime.date(2014, 3, 31)),
        source="Loi n° 2011-1906 du 21 décembre 2011, article 104",
        amount=Money(cents=40379),
    )
    """From April 1, 2013."""

    APRIL_2014 = MonthlyBase(
        period=Period(datetime.date(2014, 4, 1), datetime.date(2016, 3, 31)),
        source="Loi n° 2013-1203 du 23 décembre 2013",
        amount=Money(cents=40621),
    )
    """From April 1, 2014, not revalued in 2015."""

    APRIL_2016 = MonthlyBase(
        period=Period(datetime.date(2016, 4, 1), datetime.date(2017, 3, 31)),
        source="Circulaire N° DSS/SD2B/2016/77 du 15 mars 2016",
        amount=Money(cents=40662),
    )
    """From April 1, 2016."""

    APRIL_2017 = MonthlyBase(
        period=Period(datetime.date(2017, 4, 1), datetime.date(2018, 3, 31)),
        source="Circulaire N° DSS/SD2B/2017/97 du 21 mars 2017",
        amount=Money(cents=40784),
    )
    """From April 1, 2017."""

    APRIL_2018 = MonthlyBase(
        period=Period(datetime.date(2018, 4, 1), datetime.date(2019, 3, 31)),
        source="Instruction interministérielle N° DSS/SD2B/2018/81 du 22 mars 2018",
        amount=Money(cents=41192),
    )
    """From April 1, 2018."""

    APRIL_2019 = MonthlyBase(
        period=Period(datetime.date(2019, 4, 1), datetime.date(2020, 3, 31)),
        source="Instruction ministérielle N°DSS/SD2B/2019/65 du 25 mars 2019",
        amount=Money(cents=41316),
    )
    """From April 1, 2019."""

    APRIL_2020 = MonthlyBase(
        period=Period(datetime.date(2020, 4, 1), datetime.date(2021, 3, 31)),
        source="Instruction interministérielle no DSS/SD2B/2020/33 du 18 février 2020",
        amount=Money(cents=41440),
    )
    """From April 1, 2020."""

    APRIL_2021 = MonthlyBase(
        period=Period(datetime.date(2021, 4, 1), datetime.date(2022, 3, 31)),
        source="Instruction interministérielle n°DSS/2B/2021/65 du 19 mars 2021",
        amount=Money(cents=41481),
    )
    """From April 1, 2021."""

    APRIL_2022 = MonthlyBase(
        period=Period(datetime.date(2022, 4, 1), datetime.date(2022, 6, 30)),
        source="Instruction interministérielle n°DSS/2B/2022/82 du 28 mars 2022",
        amount=Money(cents=42228),
    )
    """From April 1, 2022."""

    JULY_2022 = MonthlyBase(
        period=Period(datetime.date(2022, 7, 1), datetime.date(2023, 3, 31)),
        source="Loi n° 2022-1158 du 16 août 2022, article 9",
        amount=Money(cents=43917),
    )
    """From July 1, 2022."""

    APRIL_2023 = MonthlyBase(
        period=Period(datetime.date(2023, 4, 1), datetime.date(2024, 3, 31)),
        source="Instruction interministérielle N° DSS/2B/2023/41 du 24 mars 2023",
        amount=Money(cents=44593),
    )
    """From April 1, 2023."""

    APRIL_2024 = MonthlyBase(
        period=Period(datetime.date(2024, 4, 1), datetime.date(2025, 3, 31)),
        source="Instruction interministérielle n° DSS/2B/2024/43 du 20 mars 2024",
        amount=Money(cents=46644),
    )
    """From April 1, 2024."""

    APRIL_2025 = MonthlyBase(
        period=Period(datetime.date(2025, 4, 1), datetime.date(2026, 3, 31)),
        source="Instruction interministérielle N° DSS/2A/2C/2025/32 du 7 mars 2025",
        amount=Money(cents=47437),
    )
    """From April 1, 2025."""

    APRIL_2026 = MonthlyBase(
        period=Period(datetime.date(2026, 4, 1)),
        source="Instruction interministérielle n° DSS/2A/2026/36 du 26 mars 2026",
        amount=Money(cents=47816),
    )
    """From April 1, 2026."""


# %% the minimum wage


@dataclass(frozen=True)
class HourlyMinimumWage(DatedValue):
    """
    The gross hourly minimum wage (*salaire minimum interprofessionnel de croissance*)
    in some territories.
    """

    amount: Money
    """The gross wage of an hour."""

    territories: frozenset[Territory]
    """The territories it is in force in."""


class MinimumWages(Enum):
    """
    The gross hourly minimum wages, the same everywhere but in Mayotte, each decree
    setting one for Mayotte and one for the other territories; Mayotte's are stated
    from 2019 only.
    """

    JULY_2005 = HourlyMinimumWage(
        period=Period(datetime.date(2005, 7, 1), datetime.date(2006, 6, 30)),
        source="Décret n° 2005-719 du 29 juin 2005",
        amount=Money(cents=803),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """July 2005 to June 2006, outside Mayotte."""

    JULY_2006 = HourlyMinimumWage(
        period=Period(datetime.date(2006, 7, 1), datetime.date(2007, 6, 30)),
        source="Décret n° 2006-751 du 29 juin 2006",
        amount=Money(cents=827),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """July 2006 to June 2007, outside Mayotte."""

    JULY_2007 = HourlyMinimumWage(
        period=Period(datetime.date(2007, 7, 1), datetime.date(2008, 4, 30)),
        source="Décret n° 2007-1052 du 28 juin 2007",
        amount=Money(cents=844),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """July 2007 to April 2008, outside Mayotte."""

    MAY_2008 = HourlyMinimumWage(
        period=Period(datetime.date(2008, 5, 1), datetime.date(2008, 6, 30)),
        source="Arrêté du 25 avril 2008 relatif au relèvement du salaire minimum de croissance",
        amount=Money(cents=863),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """May and June 2008, outside Mayotte."""

    JULY_2008 = HourlyMinimumWage(
        period=Period(datetime.date(2008, 7, 1), datetime.date(2009, 6, 30)),
        source="Décret n° 2008-617 du 27 juin 2008",
        amount=Money(cents=871),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """July 2008 to June 2009, outside Mayotte."""

    JULY_2009 = HourlyMinimumWage(
        period=Period(datetime.date(2009, 7, 1), datetime.date(2009, 12, 31)),
        source="Décret n° 2009-800 du 24 juin 2009",
        amount=Money(cents=882),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """July to December 2009, outside Mayotte."""

    YEAR_2010 = HourlyMinimumWage(
        period=Period(datetime.date(2010, 1, 1), datetime.date(2010, 12, 31)),
        source="Décret n° 2009-1584 du 17 décembre 2009",
        amount=Money(cents=886),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """2010, outside Mayotte."""

    JANUARY_2011 = HourlyMinimumWage(
        period=Period(datetime.date(2011, 1, 1), datetime.date(2011, 11, 30)),
        source="Décret n° 2010-1584 du 17 décembre 2010",
        amount=Money(cents=900),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """January to November 2011, outside Mayotte."""

    DECEMBER_2011 = HourlyMinimumWage(
        period=Period(datetime.date(2011, 12, 1), datetime.date(2011, 12, 31)),
        source="Arrêté du 29 novembre 2011 relatif au relèvement du salaire minimum de croissance",
        amount=Money(cents=919),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """December 2011, outside Mayotte."""

    JANUARY_2012 = HourlyMinimumWage(
        period=Period(datetime.date(2012, 1, 1), datetime.date(2012, 6, 30)),
        source="Décret n° 2011-1926 du 22 décembre 2011",
        amount=Money(cents=922),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """January to June 2012, outside Mayotte."""

    JULY_2012 = HourlyMinimumWage(
        period=Period(datetime.date(2012, 7, 1), datetime.date(2012, 12, 31)),
        source="Décret n° 2012-828 du 28 juin 2012",
        amount=Money(cents=940),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """July to December 2012, outside Mayotte."""

    YEAR_2013 = HourlyMinimumWage(
        period=Period(datetime.date(2013, 1, 1), datetime.date(2013, 12, 31)),
        source="Décret n° 2012-1429 du 19 décembre 2012",
        amount=Money(cents=943),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """2013, outside Mayotte."""

    YEAR_2014 = HourlyMinimumWage(
        period=Period(datetime.date(2014, 1, 1), datetime.date(2014, 12, 31)),
        source="Décret n° 2013-1190 du 19 décembre 2013",
        amount=Money(cents=953),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """2014, outside Mayotte."""

    YEAR_2015 = HourlyMinimumWage(
        period=Period(datetime.date(2015, 1, 1), datetime.date(2015, 12, 31)),
        source="Décret n° 2014-1569 du 22 décembre 2014",
        amount=Money(cents=961),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """2015, outside Mayotte."""

    YEAR_2016 = HourlyMinimumWage(
        period=Period(datetime.date(2016, 1, 1), datetime.date(2016, 12, 31)),
        source="Décret n° 2015-1688 du 17 décembre 2015",
        amount=Money(cents=967),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """2016, outside Mayotte."""

    YEAR_2017 = HourlyMinimumWage(
        period=Period(datetime.date(2017, 1, 1), datetime.date(2017, 12, 31)),
        source="Décret n° 2016-1818 du 22 décembre 2016",
        amount=Money(cents=976),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """2017, outside Mayotte."""

    YEAR_2018 = HourlyMinimumWage(
        period=Period(datetime.date(2018, 1, 1), datetime.date(2018, 12, 31)),
        source="Décret n° 2017-1719 du 20 décembre 2017",
        amount=Money(cents=988),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """2018, outside Mayotte."""

    YEAR_2019 = HourlyMinimumWage(
        period=Period(datetime.date(2019, 1, 1), datetime.date(2019, 12, 31)),
        source="Décret n° 2018-1173 du 19 décembre 2018",
        amount=Money(cents=1003),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """2019, outside Mayotte."""

    YEAR_2019_MAYOTTE = HourlyMinimumWage(
        period=Period(datetime.date(2019, 1, 1), datetime.date(2019, 12, 31)),
        source="Décret n° 2018-1173 du 19 décembre 2018",
        amount=Money(cents=757),
        territories=frozenset({Territory.MAYOTTE}),
    )
    """2019, in Mayotte."""

    YEAR_2020 = HourlyMinimumWage(
        period=Period(datetime.date(2020, 1, 1), datetime.date(2020, 12, 31)),
        source="Décret n° 2019-1387 du 18 décembre 2019",
        amount=Money(cents=1015),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """2020, outside Mayotte."""

    YEAR_2020_MAYOTTE = HourlyMinimumWage(
        period=Period(datetime.date(2020, 1, 1), datetime.date(2020, 12, 31)),
        source="Décret n° 2019-1387 du 18 décembre 2019",
        amount=Money(cents=766),
        territories=frozenset({Territory.MAYOTTE}),
    )
    """2020, in Mayotte."""

    YEAR_2021 = HourlyMinimumWage(
        period=Period(datetime.date(2021, 1, 1), datetime.date(2021, 12, 31)),
        source="Décret n° 2020-1598 du 16 décembre 2020",
        amount=Money(cents=1025),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """2021, outside Mayotte."""

    YEAR_2021_MAYOTTE = HourlyMinimumWage(
        period=Period(datetime.date(2021, 1, 1), datetime.date(2021, 12, 31)),
        source="Décret n° 2020-1598 du 16 décembre 2020",
        amount=Money(cents=774),
        territories=frozenset({Territory.MAYOTTE}),
    )
    """2021, in Mayotte."""

    JANUARY_2022 = HourlyMinimumWage(
        period=Period(datetime.date(2022, 1, 1), datetime.date(2022, 4, 30)),
        source="Décret n° 2021-1741 du 22 décembre 2021",
        amount=Money(cents=1057),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """January to April 2022, outside Mayotte."""

    JANUARY_2022_MAYOTTE = HourlyMinimumWage(
        period=Period(datetime.date(2022, 1, 1), datetime.date(2022, 4, 30)),
        source="Décret n° 2021-1741 du 22 décembre 2021",
        amount=Money(cents=798),
        territories=frozenset({Territory.MAYOTTE}),
    )
    """January to April 2022, in Mayotte."""

    MAY_2022 = HourlyMinimumWage(
        period=Period(datetime.date(2022, 5, 1), datetime.date(2022, 7, 31)),
        source="Arrêté du 19 avril 2022 relatif au relèvement du salaire minimum de croissance",
        amount=Money(cents=1085),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """May to July 2022, outside Mayotte."""

    MAY_2022_MAYOTTE = HourlyMinimumWage(
        period=Period(datetime.date(2022, 5, 1), datetime.date(2022, 7, 31)),
        source="Arrêté du 19 avril 2022 relatif au relèvement du salaire minimum de croissance",
        amount=Money(cents=819),
        territories=frozenset({Territory.MAYOTTE}),
    )
    """May to July 2022, in Mayotte."""

    AUGUST_2022 = HourlyMinimumWage(
        period=Period(datetime.date(2022, 8, 1), datetime.date(2022, 12, 31)),
        source="Arrêté du 29 juillet 2022 relatif au relèvement du salaire minimum de croissance",
        amount=Money(cents=1107),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """August to December 2022, outside Mayotte."""

    AUGUST_2022_MAYOTTE = HourlyMinimumWage(
        period=Period(datetime.date(2022, 8, 1), datetime.date(2022, 12, 31)),
        source="Arrêté du 29 juillet 2022 relatif au relèvement du salaire minimum de croissance",
        amount=Money(cents=835),
        territories=frozenset({Territory.MAYOTTE}),
    )
    """August to December 2022, in Mayotte."""

    JANUARY_2023 = HourlyMinimumWage(
        period=Period(datetime.date(2023, 1, 1), datetime.date(2023, 4, 30)),
        source="Décret n° 2022-1608 du 22 décembre 2022",
        amount=Money(cents=1127),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """January to April 2023, outside Mayotte."""

    JANUARY_2023_MAYOTTE = HourlyMinimumWage(
        period=Period(datetime.date(2023, 1, 1), datetime.date(2023, 4, 30)),
        source="Décret n° 2022-1608 du 22 décembre 2022",
        amount=Money(cents=851),
        territories=frozenset({Territory.MAYOTTE}),
    )
    """January to April 2023, in Mayotte."""

    MAY_2023 = HourlyMinimumWage(
        period=Period(datetime.date(2023, 5, 1), datetime.date(2023, 12, 31)),
        source="Arrêté du 26 avril 2023 relatif au relèvement du salaire minimum de croissance",
        amount=Money(cents=1152),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """May to December 2023, outside Mayotte."""

    MAY_2023_MAYOTTE = HourlyMinimumWage(
        period=Period(datetime.date(2023, 5, 1), datetime.date(2023, 12, 31)),
        source="Arrêté du 26 avril 2023 relatif au relèvement du salaire minimum de croissance",
        amount=Money(cents=870),
        territories=frozenset({Territory.MAYOTTE}),
    )
    """May to December 2023, in Mayotte."""

    JANUARY_2024 = HourlyMinimumWage(
        period=Period(datetime.date(2024, 1, 1), datetime.date(2024, 10, 31)),
        source="Décret n° 2023-1216 du 20 décembre 2023",
        amount=Money(cents=1165),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """January to October 2024, outside Mayotte."""

    JANUARY_2024_MAYOTTE = HourlyMinimumWage(
        period=Period(datetime.date(2024, 1, 1), datetime.date(2024, 10, 31)),
        source="Décret n° 2023-1216 du 20 décembre 2023",
        amount=Money(cents=880),
        territories=frozenset({Territory.MAYOTTE}),
    )
    """January to October 2024, in Mayotte."""

    NOVEMBER_2024 = HourlyMinimumWage(
        period=Period(datetime.date(2024, 11, 1), datetime.date(2025, 12, 31)),
        source="Décret n° 2024-951 du 23 octobre 2024",
        amount=Money(cents=1188),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """November 2024 to December 2025, outside Mayotte."""

    JANUARY_2026 = HourlyMinimumWage(
        period=Period(datetime.date(2026, 1, 1), datetime.date(2026, 5, 31)),
        source="Décret n° 2025-1228 du 17 décembre 2025",
        amount=Money(cents=1202),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """January to May 2026, outside Mayotte."""

    JUNE_2026 = HourlyMinimumWage(
        period=Period(datetime.date(2026, 6, 1)),
        source="Arrêté du 22 mai 2026 relatif au relèvement du salaire minimum de croissance",
        amount=Money(cents=1231),
        territories=frozenset(set(Territory) - {Territory.MAYOTTE}),
    )
    """From June 2026, outside Mayotte."""

    NOVEMBER_2024_MAYOTTE = HourlyMinimumWage(
        period=Period(datetime.date(2024, 11, 1)),
        source="Décret n° 2024-951 du 23 octobre 2024",
        amount=Money(cents=898),
        territories=frozenset({Territory.MAYOTTE}),
    )
    """From November 2024, in Mayotte."""


# %% resource ceilings


@dataclass(frozen=True)
class ResourceCeilings(DatedValue):
    """
    The two ceilings on a household's yearly resources that set its bracket for family
    allowances, each raised by the same amount for every child in its charge.
    """

    first_ceiling: Money
    """The ceiling of I of `D521-3 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000044809227>`__, before the raise for children."""

    second_ceiling: Money
    """The ceiling of II of `D521-3 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000044809227>`__, before the raise for children."""

    raise_per_child: Money
    """What each ceiling is raised by for every child in the household's charge."""


class ResourceCeilingRevaluations(Enum):
    """
    The ceilings revalued for a calendar year by III of
    `D521-3 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000044809227>`__.
    """

    YEAR_2018 = ResourceCeilings(
        period=Period(datetime.date(2018, 1, 1), datetime.date(2018, 12, 31)),
        source="Circulaire interministérielle N° DSS/SD2B/2017/352 du 22 décembre 2017",
        first_ceiling=Money.from_euros(56286),
        second_ceiling=Money.from_euros(78770),
        raise_per_child=Money.from_euros(5628),
    )
    """2018."""

    YEAR_2019 = ResourceCeilings(
        period=Period(datetime.date(2019, 1, 1), datetime.date(2019, 12, 31)),
        source="Instruction interministérielle n° DSS/SD2B/2018/279 du 17 décembre 2018",
        first_ceiling=Money.from_euros(56849),
        second_ceiling=Money.from_euros(79558),
        raise_per_child=Money.from_euros(5684),
    )
    """2019."""

    YEAR_2020 = ResourceCeilings(
        period=Period(datetime.date(2020, 1, 1), datetime.date(2020, 12, 31)),
        source="Instruction interministerielle no DSS/SD2B/2019/261 du 18 décembre 2019",
        first_ceiling=Money.from_euros(57759),
        second_ceiling=Money.from_euros(80831),
        raise_per_child=Money.from_euros(5775),
    )
    """2020."""

    YEAR_2021 = ResourceCeilings(
        period=Period(datetime.date(2021, 1, 1), datetime.date(2021, 12, 31)),
        source="Arrêté du 14 décembre 2020, article 1",
        first_ceiling=Money.from_euros(58279),
        second_ceiling=Money.from_euros(81558),
        raise_per_child=Money.from_euros(5827),
    )
    """2021."""


# %% the rates of Mayotte


@dataclass(frozen=True)
class MayotteRates(DatedValue):
    """
    The rates of the monthly base that family allowances in Mayotte pay for the first,
    second and third child, raised year by year towards those of article 7 of the
    décret n°2002-423.
    """

    first_child: Fraction
    """The rate for a household with one child, which had none in its charge before 2012."""

    second_child: Fraction
    """The rate for the second child."""

    third_child: Fraction
    """The rate for the third child."""


class MayotteRateSchedule(Enum):
    """
    The rates of the annex to the décret n°2002-423 (LEGIARTI000036326574), from 2011
    to 2020, each for a calendar year.
    """

    YEAR_2011 = MayotteRates(
        period=Period(datetime.date(2011, 1, 1), datetime.date(2011, 12, 31)),
        source="Décret n°2002-423, annexe",
        first_child=Fraction("14.50") / 100,
        second_child=Fraction("23.2") / 100,
        third_child=Fraction("4.63") / 100,
    )
    """2011."""

    YEAR_2012 = MayotteRates(
        period=Period(datetime.date(2012, 1, 1), datetime.date(2012, 12, 31)),
        source="Décret n°2002-423, annexe",
        first_child=Fraction("13.93") / 100,
        second_child=Fraction("23.79") / 100,
        third_child=Fraction("5.39") / 100,
    )
    """2012."""

    YEAR_2013 = MayotteRates(
        period=Period(datetime.date(2013, 1, 1), datetime.date(2013, 12, 31)),
        source="Décret n°2002-423, annexe",
        first_child=Fraction("13.35") / 100,
        second_child=Fraction("24.37") / 100,
        third_child=Fraction("6.15") / 100,
    )
    """2013."""

    YEAR_2014 = MayotteRates(
        period=Period(datetime.date(2014, 1, 1), datetime.date(2014, 12, 31)),
        source="Décret n°2002-423, annexe",
        first_child=Fraction("12.78") / 100,
        second_child=Fraction("24.96") / 100,
        third_child=Fraction("6.90") / 100,
    )
    """2014."""

    YEAR_2015 = MayotteRates(
        period=Period(datetime.date(2015, 1, 1), datetime.date(2015, 12, 31)),
        source="Décret n°2002-423, annexe",
        first_child=Fraction("12.20") / 100,
        second_child=Fraction("25.55") / 100,
        third_child=Fraction("7.66") / 100,
    )
    """2015."""

    YEAR_2016 = MayotteRates(
        period=Period(datetime.date(2016, 1, 1), datetime.date(2016, 12, 31)),
        source="Décret n°2002-423, annexe",
        first_child=Fraction("11.63") / 100,
        second_child=Fraction("26.13") / 100,
        third_child=Fraction("8.42") / 100,
    )
    """2016."""

    YEAR_2017 = MayotteRates(
        period=Period(datetime.date(2017, 1, 1), datetime.date(2017, 12, 31)),
        source="Décret n°2002-423, annexe",
        first_child=Fraction("11.05") / 100,
        second_child=Fraction("26.72") / 100,
        third_child=Fraction("9.18") / 100,
    )
    """2017."""

    YEAR_2018 = MayotteRates(
        period=Period(datetime.date(2018, 1, 1), datetime.date(2018, 12, 31)),
        source="Décret n°2002-423, annexe",
        first_child=Fraction("9.76") / 100,
        second_child=Fraction("28.04") / 100,
        third_child=Fraction("10.89") / 100,
    )
    """2018."""

    YEAR_2019 = MayotteRates(
        period=Period(datetime.date(2019, 1, 1), datetime.date(2019, 12, 31)),
        source="Décret n°2002-423, annexe",
        first_child=Fraction("8.47") / 100,
        second_child=Fraction("29.36") / 100,
        third_child=Fraction("12.59") / 100,
    )
    """2019."""

    YEAR_2020 = MayotteRates(
        period=Period(datetime.date(2020, 1, 1), datetime.date(2020, 12, 31)),
        source="Décret n°2002-423, annexe",
        first_child=Fraction("7.17") / 100,
        second_child=Fraction("30.68") / 100,
        third_child=Fraction("14.30") / 100,
    )
    """2020."""
