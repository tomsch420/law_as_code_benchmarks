"""
The scales the arrêté of September 27, 2019 sets for the personal housing aids of rented
homes, each in force for a period: the rent ceilings, flat charges, minimum
participation, reference rents and family rates (articles 7 to 16), the income
abatements (article 15) and the overseas scales (articles 46 and 47).
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from krrood.entity_query_language.predicate import symbolic_function

from law_as_code_benchmarks.catala.domain import DatedValue
from law_as_code_benchmarks.law.period import Period
from law_as_code_benchmarks.catala.housing.domain import HousingZone
from law_as_code_benchmarks.catala.money import Money

# %% amounts by zone


@dataclass(frozen=True)
class ZoneAmounts:
    """An amount for each geographic zone."""

    zone_1: Money
    """The amount in zone I."""

    zone_2: Money
    """The amount in zone II."""

    zone_3: Money
    """The amount in zone III."""

    @classmethod
    def from_cents(cls, zone_1: int, zone_2: int, zone_3: int) -> ZoneAmounts:
        """:return: The amounts of *zone_1*, *zone_2* and *zone_3* cents."""
        return cls(
            zone_1=Money(cents=zone_1),
            zone_2=Money(cents=zone_2),
            zone_3=Money(cents=zone_3),
        )

    @staticmethod
    @symbolic_function
    def amount_in(amounts: ZoneAmounts, zone: HousingZone) -> Money:
        """:return: The amount of *amounts* in *zone*."""
        match zone:
            case HousingZone.ZONE_1:
                return amounts.zone_1
            case HousingZone.ZONE_2:
                return amounts.zone_2
            case HousingZone.ZONE_3:
                return amounts.zone_3


# %% scales by household


@dataclass(frozen=True)
class HouseholdAmounts:
    """An amount for a person alone, a couple, one dependant, and more for each further one."""

    single: Money
    """For a person alone without dependants."""

    couple: Money
    """For a couple without dependants."""

    one_dependant: Money
    """For a household with one dependant."""

    each_further_dependant: Money
    """Added for each dependant after the first."""


@dataclass(frozen=True)
class RentCeilings:
    """The rent ceilings of a person alone, a couple, one dependant and each further one, by zone."""

    single: ZoneAmounts
    """For a person alone without dependants."""

    couple: ZoneAmounts
    """For a couple without dependants."""

    one_dependant: ZoneAmounts
    """For a household with one dependant."""

    each_further_dependant: ZoneAmounts
    """Added for each dependant after the first."""


@dataclass(frozen=True)
class ReferenceRents(HouseholdAmounts):
    """The reference rents of article 14 the rent ratio is taken against."""


@dataclass(frozen=True)
class FamilyRates:
    """
    The family composition rates of article 14: of a person alone and a couple without
    dependants, by number of dependants up to some, and the change for each further one.
    """

    single: Fraction
    """Of a person alone without dependants."""

    couple: Fraction
    """Of a couple without dependants."""

    by_dependants: tuple[Fraction, ...]
    """Of one dependant, two, and so on."""

    each_further_dependant: Fraction
    """The change for each dependant beyond those :attr:`by_dependants` lists."""

    @staticmethod
    @symbolic_function
    def rate_for(rates: FamilyRates, couple: bool, dependants: int) -> Fraction:
        """:return: The rate of *rates* for a couple or a person alone with *dependants*."""
        if dependants == 0:
            return rates.couple if couple else rates.single
        listed = len(rates.by_dependants)
        if dependants <= listed:
            return rates.by_dependants[dependants - 1]
        return rates.by_dependants[-1] + rates.each_further_dependant * (
            dependants - listed
        )


class FamilyRateScales(Enum):
    """The family composition rates, the same in every version of the arrêté."""

    METROPOLITAN = FamilyRates(
        single=Fraction(283, 10000),
        couple=Fraction(315, 10000),
        by_dependants=(
            Fraction(270, 10000),
            Fraction(238, 10000),
            Fraction(201, 10000),
            Fraction(185, 10000),
            Fraction(179, 10000),
            Fraction(173, 10000),
        ),
        each_further_dependant=Fraction(-6, 10000),
    )
    """Article 14."""

    OVERSEAS_BEFORE_2023 = FamilyRates(
        single=Fraction(281, 10000),
        couple=Fraction(299, 10000),
        by_dependants=(
            Fraction(238, 10000),
            Fraction(217, 10000),
            Fraction(194, 10000),
            Fraction(180, 10000),
            Fraction(169, 10000),
            Fraction(162, 10000),
        ),
        each_further_dependant=Fraction(0),
    )
    """Article 46 until 2022, the rate of six dependants holding beyond."""

    OVERSEAS = FamilyRates(
        single=Fraction(281, 10000),
        couple=Fraction(299, 10000),
        by_dependants=(
            Fraction(238, 10000),
            Fraction(217, 10000),
            Fraction(194, 10000),
            Fraction(180, 10000),
            Fraction(169, 10000),
            Fraction(162, 10000),
            Fraction(167, 10000),
        ),
        each_further_dependant=Fraction(-6, 10000),
    )
    """Article 46 from 2023."""


# %% articles 7 to 16


@dataclass(frozen=True)
class RentedHomeScale(DatedValue):
    """The amounts of articles 7 to 16 for rented homes in metropolitan France."""

    ceilings: RentCeilings
    """Article 7: the rent ceilings."""

    room_ceiling: ZoneAmounts
    """Article 8: the rent ceiling of a room."""

    hosted_room_ceiling: ZoneAmounts
    """Article 8: that of a room of elderly or disabled adults lodged by private persons for payment."""

    shared_ceilings: RentCeilings
    """Article 16: the rent ceilings of a shared dwelling."""

    charges: Money
    """Article 9: the flat charges without dependants, and article 16's of a couple sharing."""

    shared_charges_single: Money
    """Article 16: the flat charges of a person alone sharing."""

    charges_per_dependant: Money
    """Articles 9 and 16: the flat charges added for each dependant."""

    minimum_participation: Money
    """Article 13: the least minimum participation."""

    reference_rents: ReferenceRents
    """Article 14: the reference rents."""


class RentedHomeScales(Enum):
    """The versions of articles 7 to 16, revalued every October and in July 2022."""

    OCTOBER_2020 = RentedHomeScale(
        period=Period(datetime.date(2020, 10, 1), datetime.date(2021, 9, 30)),
        source="Arrêté du 27 septembre 2019, articles 7 à 16 (LEGIARTI000042378448)",
        ceilings=RentCeilings(
            single=ZoneAmounts.from_cents(29682, 25869, 24246),
            couple=ZoneAmounts.from_cents(35799, 31664, 29392),
            one_dependant=ZoneAmounts.from_cents(40460, 35630, 32956),
            each_further_dependant=ZoneAmounts.from_cents(5870, 5186, 4723),
        ),
        room_ceiling=ZoneAmounts.from_cents(26714, 23282, 21821),
        hosted_room_ceiling=ZoneAmounts.from_cents(22262, 19402, 18185),
        shared_ceilings=RentCeilings(
            single=ZoneAmounts.from_cents(22262, 19402, 18185),
            couple=ZoneAmounts.from_cents(26849, 23748, 22044),
            one_dependant=ZoneAmounts.from_cents(30345, 26723, 24717),
            each_further_dependant=ZoneAmounts.from_cents(4403, 3890, 3542),
        ),
        charges=Money(cents=5399),
        shared_charges_single=Money(cents=2699),
        charges_per_dependant=Money(cents=1224),
        minimum_participation=Money(cents=3524),
        reference_rents=ReferenceRents(
            single=Money(cents=25869),
            couple=Money(cents=31664),
            one_dependant=Money(cents=35630),
            each_further_dependant=Money(cents=5186),
        ),
    )
    """From 1/10/2020."""

    OCTOBER_2021 = RentedHomeScale(
        period=Period(datetime.date(2021, 10, 1), datetime.date(2022, 6, 30)),
        source="Arrêté du 27 septembre 2019, articles 7 à 16 (LEGIARTI000044137432)",
        ceilings=RentCeilings(
            single=ZoneAmounts.from_cents(29807, 25978, 24348),
            couple=ZoneAmounts.from_cents(35949, 31797, 29515),
            one_dependant=ZoneAmounts.from_cents(40630, 35780, 33094),
            each_further_dependant=ZoneAmounts.from_cents(5895, 5208, 4743),
        ),
        room_ceiling=ZoneAmounts.from_cents(26826, 23380, 21913),
        hosted_room_ceiling=ZoneAmounts.from_cents(22355, 19484, 18261),
        shared_ceilings=RentCeilings(
            single=ZoneAmounts.from_cents(22355, 19484, 18261),
            couple=ZoneAmounts.from_cents(26962, 23848, 22136),
            one_dependant=ZoneAmounts.from_cents(30473, 26835, 24821),
            each_further_dependant=ZoneAmounts.from_cents(4421, 3906, 3557),
        ),
        charges=Money(cents=5422),
        shared_charges_single=Money(cents=2710),
        charges_per_dependant=Money(cents=1229),
        minimum_participation=Money(cents=3539),
        reference_rents=ReferenceRents(
            single=Money(cents=25978),
            couple=Money(cents=31797),
            one_dependant=Money(cents=35780),
            each_further_dependant=Money(cents=5208),
        ),
    )
    """From 1/10/2021."""

    JULY_2022 = RentedHomeScale(
        period=Period(datetime.date(2022, 7, 1), datetime.date(2023, 9, 30)),
        source="Arrêté du 27 septembre 2019, articles 7 à 16 (LEGIARTI000046206217)",
        ceilings=RentCeilings(
            single=ZoneAmounts.from_cents(30850, 26887, 25200),
            couple=ZoneAmounts.from_cents(37207, 32910, 30548),
            one_dependant=ZoneAmounts.from_cents(42052, 37032, 34252),
            each_further_dependant=ZoneAmounts.from_cents(6101, 5390, 4909),
        ),
        room_ceiling=ZoneAmounts.from_cents(27765, 24198, 22680),
        hosted_room_ceiling=ZoneAmounts.from_cents(23138, 20165, 18900),
        shared_ceilings=RentCeilings(
            single=ZoneAmounts.from_cents(23138, 20165, 18900),
            couple=ZoneAmounts.from_cents(27905, 24683, 22911),
            one_dependant=ZoneAmounts.from_cents(31539, 27774, 25689),
            each_further_dependant=ZoneAmounts.from_cents(4576, 4043, 3682),
        ),
        charges=Money(cents=5612),
        shared_charges_single=Money(cents=2805),
        charges_per_dependant=Money(cents=1272),
        minimum_participation=Money(cents=3663),
        reference_rents=ReferenceRents(
            single=Money(cents=26887),
            couple=Money(cents=32910),
            one_dependant=Money(cents=37032),
            each_further_dependant=Money(cents=5390),
        ),
    )
    """From 1/7/2022."""

    OCTOBER_2023 = RentedHomeScale(
        period=Period(datetime.date(2023, 10, 1), datetime.date(2024, 9, 30)),
        source="Arrêté du 27 septembre 2019, articles 7 à 16 (LEGIARTI000048109313)",
        ceilings=RentCeilings(
            single=ZoneAmounts.from_cents(31930, 27828, 26082),
            couple=ZoneAmounts.from_cents(38509, 34062, 31617),
            one_dependant=ZoneAmounts.from_cents(43524, 38328, 35451),
            each_further_dependant=ZoneAmounts.from_cents(6315, 5579, 5081),
        ),
        room_ceiling=ZoneAmounts.from_cents(28737, 25045, 23474),
        hosted_room_ceiling=ZoneAmounts.from_cents(23948, 20871, 19562),
        shared_ceilings=RentCeilings(
            single=ZoneAmounts.from_cents(23948, 20871, 19562),
            couple=ZoneAmounts.from_cents(28882, 25547, 23713),
            one_dependant=ZoneAmounts.from_cents(32643, 28746, 26588),
            each_further_dependant=ZoneAmounts.from_cents(4736, 4184, 3811),
        ),
        charges=Money(cents=5808),
        shared_charges_single=Money(cents=2903),
        charges_per_dependant=Money(cents=1317),
        minimum_participation=Money(cents=3791),
        reference_rents=ReferenceRents(
            single=Money(cents=27828),
            couple=Money(cents=34062),
            one_dependant=Money(cents=38328),
            each_further_dependant=Money(cents=5579),
        ),
    )
    """From 1/10/2023."""

    OCTOBER_2024 = RentedHomeScale(
        period=Period(datetime.date(2024, 10, 1), datetime.date(2025, 9, 30)),
        source="Arrêté du 27 septembre 2019, articles 7 à 16 (LEGIARTI000050286647)",
        ceilings=RentCeilings(
            single=ZoneAmounts.from_cents(32971, 28735, 26932),
            couple=ZoneAmounts.from_cents(39764, 35172, 32648),
            one_dependant=ZoneAmounts.from_cents(44943, 39577, 36607),
            each_further_dependant=ZoneAmounts.from_cents(6521, 5761, 5247),
        ),
        room_ceiling=ZoneAmounts.from_cents(29674, 25862, 24239),
        hosted_room_ceiling=ZoneAmounts.from_cents(24728, 21551, 20199),
        shared_ceilings=RentCeilings(
            single=ZoneAmounts.from_cents(24728, 21551, 20199),
            couple=ZoneAmounts.from_cents(29823, 26379, 24486),
            one_dependant=ZoneAmounts.from_cents(33707, 29683, 27455),
            each_further_dependant=ZoneAmounts.from_cents(4891, 4321, 3935),
        ),
        charges=Money(cents=5997),
        shared_charges_single=Money(cents=2998),
        charges_per_dependant=Money(cents=1360),
        minimum_participation=Money(cents=3915),
        reference_rents=ReferenceRents(
            single=Money(cents=28735),
            couple=Money(cents=35172),
            one_dependant=Money(cents=39577),
            each_further_dependant=Money(cents=5761),
        ),
    )
    """From 1/10/2024."""

    OCTOBER_2025 = RentedHomeScale(
        period=Period(datetime.date(2025, 10, 1), None),
        source="Arrêté du 27 septembre 2019, articles 7 à 16 (LEGIARTI000052233874)",
        ceilings=RentCeilings(
            single=ZoneAmounts.from_cents(33314, 29034, 27212),
            couple=ZoneAmounts.from_cents(40178, 35538, 32988),
            one_dependant=ZoneAmounts.from_cents(45410, 39989, 36988),
            each_further_dependant=ZoneAmounts.from_cents(6589, 5821, 5301),
        ),
        room_ceiling=ZoneAmounts.from_cents(29983, 26131, 24491),
        hosted_room_ceiling=ZoneAmounts.from_cents(24986, 21776, 20409),
        shared_ceilings=RentCeilings(
            single=ZoneAmounts.from_cents(24986, 21776, 20409),
            couple=ZoneAmounts.from_cents(30134, 26654, 24741),
            one_dependant=ZoneAmounts.from_cents(34058, 29992, 27741),
            each_further_dependant=ZoneAmounts.from_cents(4942, 4366, 3976),
        ),
        charges=Money(cents=6059),
        shared_charges_single=Money(cents=3029),
        charges_per_dependant=Money(cents=1374),
        minimum_participation=Money(cents=3956),
        reference_rents=ReferenceRents(
            single=Money(cents=29034),
            couple=Money(cents=35538),
            one_dependant=Money(cents=39989),
            each_further_dependant=Money(cents=5821),
        ),
    )
    """From 1/10/2025."""


# %% article 15 and 47


@dataclass(frozen=True)
class IncomeAbatements(DatedValue):
    """The flat abatements of the household's resources of D823-17 (*R0*), by household."""

    single: Money
    """Of a person alone without dependants."""

    couple: Money
    """Of a couple without dependants."""

    by_dependants: tuple[Money, ...]
    """Of one dependant, two, and so on."""

    each_further_dependant: Money
    """Added for each dependant beyond those :attr:`by_dependants` lists."""

    @staticmethod
    @symbolic_function
    def abatement_for(
        abatements: IncomeAbatements, couple: bool, dependants: int
    ) -> Money:
        """:return: The abatement of *abatements* for a couple or a person alone with *dependants*."""
        if dependants == 0:
            return abatements.couple if couple else abatements.single
        listed = len(abatements.by_dependants)
        if dependants <= listed:
            return abatements.by_dependants[dependants - 1]
        return abatements.by_dependants[-1] + abatements.each_further_dependant * (
            dependants - listed
        )


class IncomeAbatementScales(Enum):
    """The versions of article 15, revalued every January and in July 2022."""

    JANUARY_2020 = IncomeAbatements(
        period=Period(datetime.date(2020, 1, 1), datetime.date(2021, 12, 31)),
        source="Arrêté du 27 septembre 2019, article 15 (LEGIARTI000041489192)",
        single=Money.from_euros(4588),
        couple=Money.from_euros(6572),
        by_dependants=(
            Money.from_euros(7839),
            Money.from_euros(8015),
            Money.from_euros(8322),
            Money.from_euros(8631),
            Money.from_euros(8938),
            Money.from_euros(9246),
        ),
        each_further_dependant=Money.from_euros(305),
    )
    """From 1/1/2020."""

    JANUARY_2022 = IncomeAbatements(
        period=Period(datetime.date(2022, 1, 1), datetime.date(2022, 6, 30)),
        source="Arrêté du 27 septembre 2019, article 15 (LEGIARTI000045011468)",
        single=Money.from_euros(4683),
        couple=Money.from_euros(6709),
        by_dependants=(
            Money.from_euros(8002),
            Money.from_euros(8182),
            Money.from_euros(8495),
            Money.from_euros(8811),
            Money.from_euros(9124),
            Money.from_euros(9439),
        ),
        each_further_dependant=Money.from_euros(311),
    )
    """From 1/1/2022."""

    JULY_2022 = IncomeAbatements(
        period=Period(datetime.date(2022, 7, 1), datetime.date(2022, 12, 31)),
        source="Arrêté du 27 septembre 2019, article 15 (LEGIARTI000046126962)",
        single=Money.from_euros(4870),
        couple=Money.from_euros(6977),
        by_dependants=(
            Money.from_euros(8322),
            Money.from_euros(8509),
            Money.from_euros(8834),
            Money.from_euros(9163),
            Money.from_euros(9488),
            Money.from_euros(9816),
        ),
        each_further_dependant=Money.from_euros(323),
    )
    """From 1/7/2022."""

    JANUARY_2023 = IncomeAbatements(
        period=Period(datetime.date(2023, 1, 1), datetime.date(2023, 12, 31)),
        source="Arrêté du 27 septembre 2019, article 15 (LEGIARTI000046834762)",
        single=Money.from_euros(4949),
        couple=Money.from_euros(7090),
        by_dependants=(
            Money.from_euros(8456),
            Money.from_euros(8646),
            Money.from_euros(8977),
            Money.from_euros(9311),
            Money.from_euros(9642),
            Money.from_euros(9975),
        ),
        each_further_dependant=Money.from_euros(328),
    )
    """From 1/1/2023."""

    JANUARY_2024 = IncomeAbatements(
        period=Period(datetime.date(2024, 1, 1), datetime.date(2024, 12, 31)),
        source="Arrêté du 27 septembre 2019, article 15 (LEGIARTI000048656246)",
        single=Money.from_euros(5186),
        couple=Money.from_euros(7430),
        by_dependants=(
            Money.from_euros(8862),
            Money.from_euros(9061),
            Money.from_euros(9408),
            Money.from_euros(9758),
            Money.from_euros(10105),
            Money.from_euros(10454),
        ),
        each_further_dependant=Money.from_euros(343),
    )
    """From 1/1/2024."""

    JANUARY_2025 = IncomeAbatements(
        period=Period(datetime.date(2025, 1, 1), None),
        source="Arrêté du 27 septembre 2019, article 15 (LEGIARTI000050931814)",
        single=Money.from_euros(5235),
        couple=Money.from_euros(7501),
        by_dependants=(
            Money.from_euros(8947),
            Money.from_euros(9148),
            Money.from_euros(9498),
            Money.from_euros(9851),
            Money.from_euros(10202),
            Money.from_euros(10554),
        ),
        each_further_dependant=Money.from_euros(346),
    )
    """From 1/1/2025."""


class SaintPierreAbatementScales(Enum):
    """The versions of article 47 for Saint-Pierre-et-Miquelon, from July 2022."""

    JULY_2022 = IncomeAbatements(
        period=Period(datetime.date(2022, 7, 1), datetime.date(2022, 12, 31)),
        source="Arrêté du 27 septembre 2019, article 47 (LEGIARTI000046126954)",
        single=Money.from_euros(4870),
        couple=Money.from_euros(6977),
        by_dependants=(
            Money.from_euros(8322),
            Money.from_euros(8509),
            Money.from_euros(8834),
            Money.from_euros(9163),
            Money.from_euros(9488),
            Money.from_euros(9816),
        ),
        each_further_dependant=Money.from_euros(323),
    )
    """From 1/7/2022."""

    JANUARY_2023 = IncomeAbatements(
        period=Period(datetime.date(2023, 1, 1), datetime.date(2023, 12, 31)),
        source="Arrêté du 27 septembre 2019, article 47 (LEGIARTI000046834753)",
        single=Money.from_euros(5272),
        couple=Money.from_euros(7552),
        by_dependants=(
            Money.from_euros(9008),
            Money.from_euros(9211),
            Money.from_euros(9563),
            Money.from_euros(9919),
            Money.from_euros(10271),
            Money.from_euros(10626),
        ),
        each_further_dependant=Money.from_euros(350),
    )
    """From 1/1/2023."""

    JANUARY_2024 = IncomeAbatements(
        period=Period(datetime.date(2024, 1, 1), datetime.date(2024, 12, 31)),
        source="Arrêté du 27 septembre 2019, article 47 (LEGIARTI000048656240)",
        single=Money.from_euros(5335),
        couple=Money.from_euros(7643),
        by_dependants=(
            Money.from_euros(9116),
            Money.from_euros(9322),
            Money.from_euros(9678),
            Money.from_euros(10039),
            Money.from_euros(10395),
            Money.from_euros(10754),
        ),
        each_further_dependant=Money.from_euros(354),
    )
    """From 1/1/2024."""

    JANUARY_2025 = IncomeAbatements(
        period=Period(datetime.date(2025, 1, 1), None),
        source="Arrêté du 27 septembre 2019, article 47 (LEGIARTI000050931796)",
        single=Money.from_euros(5507),
        couple=Money.from_euros(7889),
        by_dependants=(
            Money.from_euros(9410),
            Money.from_euros(9623),
            Money.from_euros(9990),
            Money.from_euros(10363),
            Money.from_euros(10730),
            Money.from_euros(11101),
        ),
        each_further_dependant=Money.from_euros(365),
    )
    """From 1/1/2025."""


class MayotteAbatementScales(Enum):
    """The versions of article 47 for Mayotte in 2020 and 2021, the abatement of six dependants holding beyond."""

    JANUARY_2020 = IncomeAbatements(
        period=Period(datetime.date(2020, 1, 1), datetime.date(2020, 12, 31)),
        source="Arrêté du 27 septembre 2019, article 47 (LEGIARTI000041489186)",
        single=Money.from_euros(3960),
        couple=Money.from_euros(5673),
        by_dependants=(
            Money.from_euros(6396),
            Money.from_euros(6849),
            Money.from_euros(7386),
            Money.from_euros(7935),
            Money.from_euros(8484),
            Money.from_euros(9032),
        ),
        each_further_dependant=Money.from_euros(0),
    )
    """From 1/1/2020."""

    JANUARY_2021 = IncomeAbatements(
        period=Period(datetime.date(2021, 1, 1), datetime.date(2021, 12, 31)),
        source="Arrêté du 27 septembre 2019, article 47 (LEGIARTI000043044380)",
        single=Money.from_euros(4274),
        couple=Money.from_euros(6122),
        by_dependants=(
            Money.from_euros(6990),
            Money.from_euros(7432),
            Money.from_euros(7854),
            Money.from_euros(8283),
            Money.from_euros(8711),
            Money.from_euros(9139),
        ),
        each_further_dependant=Money.from_euros(0),
    )
    """From 1/1/2021."""


# %% article 46


@dataclass(frozen=True)
class OverseasScale(DatedValue):
    """The amounts article 46 sets in the overseas departments, Saint-Barthélemy and Saint-Martin."""

    one_dependant_abatement: Money
    """The abatement of resources of a household with one dependant."""

    charges: Money
    """The flat charges without dependants, and those of a couple sharing."""

    shared_charges_single: Money
    """The flat charges of a person alone sharing."""

    charges_per_dependant: Money
    """The flat charges added for each dependant."""

    family_rates: FamilyRates
    """The family composition rates."""

    dependants_counted_at_most: int | None
    """How many dependants the ceilings, reference rents, abatements and charges count at most; None where all count."""


class OverseasScales(Enum):
    """The versions of article 46."""

    OCTOBER_2020 = OverseasScale(
        period=Period(datetime.date(2020, 10, 1), datetime.date(2021, 9, 30)),
        source="Arrêté du 27 septembre 2019, article 46 (LEGIARTI000042378415)",
        one_dependant_abatement=Money.from_euros(7584),
        charges=Money(cents=3625),
        shared_charges_single=Money(cents=1864),
        charges_per_dependant=Money(cents=932),
        family_rates=FamilyRateScales.OVERSEAS_BEFORE_2023.value,
        dependants_counted_at_most=6,
    )
    """From 1/10/2020."""

    OCTOBER_2021 = OverseasScale(
        period=Period(datetime.date(2021, 10, 1), datetime.date(2021, 12, 31)),
        source="Arrêté du 27 septembre 2019, article 46 (LEGIARTI000044137389)",
        one_dependant_abatement=Money.from_euros(7584),
        charges=Money(cents=3640),
        shared_charges_single=Money(cents=1872),
        charges_per_dependant=Money(cents=936),
        family_rates=FamilyRateScales.OVERSEAS_BEFORE_2023.value,
        dependants_counted_at_most=6,
    )
    """From 1/10/2021."""

    JANUARY_2022 = OverseasScale(
        period=Period(datetime.date(2022, 1, 1), datetime.date(2022, 6, 30)),
        source="Arrêté du 27 septembre 2019, article 46 (LEGIARTI000045011463)",
        one_dependant_abatement=Money.from_euros(7742),
        charges=Money(cents=3640),
        shared_charges_single=Money(cents=1872),
        charges_per_dependant=Money(cents=936),
        family_rates=FamilyRateScales.OVERSEAS_BEFORE_2023.value,
        dependants_counted_at_most=6,
    )
    """From 1/1/2022."""

    JULY_2022 = OverseasScale(
        period=Period(datetime.date(2022, 7, 1), datetime.date(2022, 12, 31)),
        source="Arrêté du 27 septembre 2019, article 46 (LEGIARTI000046206183)",
        one_dependant_abatement=Money.from_euros(8051),
        charges=Money(cents=3767),
        shared_charges_single=Money(cents=1938),
        charges_per_dependant=Money(cents=969),
        family_rates=FamilyRateScales.OVERSEAS_BEFORE_2023.value,
        dependants_counted_at_most=6,
    )
    """From 1/7/2022."""

    JANUARY_2023 = OverseasScale(
        period=Period(datetime.date(2023, 1, 1), datetime.date(2023, 9, 30)),
        source="Arrêté du 27 septembre 2019, article 46 (LEGIARTI000046834756)",
        one_dependant_abatement=Money.from_euros(8181),
        charges=Money(cents=3767),
        shared_charges_single=Money(cents=1938),
        charges_per_dependant=Money(cents=969),
        family_rates=FamilyRateScales.OVERSEAS.value,
        dependants_counted_at_most=None,
    )
    """From 1/1/2023."""

    OCTOBER_2023 = OverseasScale(
        period=Period(datetime.date(2023, 10, 1), datetime.date(2023, 12, 31)),
        source="Arrêté du 27 septembre 2019, article 46 (LEGIARTI000048109272)",
        one_dependant_abatement=Money.from_euros(8181),
        charges=Money(cents=3899),
        shared_charges_single=Money(cents=2006),
        charges_per_dependant=Money(cents=1003),
        family_rates=FamilyRateScales.OVERSEAS.value,
        dependants_counted_at_most=None,
    )
    """From 1/10/2023."""

    JANUARY_2024 = OverseasScale(
        period=Period(datetime.date(2024, 1, 1), datetime.date(2024, 9, 30)),
        source="Arrêté du 27 septembre 2019, article 46 (LEGIARTI000048656243)",
        one_dependant_abatement=Money.from_euros(8574),
        charges=Money(cents=3899),
        shared_charges_single=Money(cents=2006),
        charges_per_dependant=Money(cents=1003),
        family_rates=FamilyRateScales.OVERSEAS.value,
        dependants_counted_at_most=None,
    )
    """From 1/1/2024."""

    OCTOBER_2024 = OverseasScale(
        period=Period(datetime.date(2024, 10, 1), datetime.date(2024, 12, 31)),
        source="Arrêté du 27 septembre 2019, article 46 (LEGIARTI000050286587)",
        one_dependant_abatement=Money.from_euros(8574),
        charges=Money(cents=4026),
        shared_charges_single=Money(cents=2071),
        charges_per_dependant=Money(cents=1036),
        family_rates=FamilyRateScales.OVERSEAS.value,
        dependants_counted_at_most=None,
    )
    """From 1/10/2024."""

    JANUARY_2025 = OverseasScale(
        period=Period(datetime.date(2025, 1, 1), datetime.date(2025, 9, 30)),
        source="Arrêté du 27 septembre 2019, article 46 (LEGIARTI000050931798)",
        one_dependant_abatement=Money.from_euros(8656),
        charges=Money(cents=4026),
        shared_charges_single=Money(cents=2071),
        charges_per_dependant=Money(cents=1036),
        family_rates=FamilyRateScales.OVERSEAS.value,
        dependants_counted_at_most=None,
    )
    """From 1/1/2025."""

    OCTOBER_2025 = OverseasScale(
        period=Period(datetime.date(2025, 10, 1), None),
        source="Arrêté du 27 septembre 2019, article 46 (LEGIARTI000052233795)",
        one_dependant_abatement=Money.from_euros(8656),
        charges=Money(cents=4068),
        shared_charges_single=Money(cents=2093),
        charges_per_dependant=Money(cents=1047),
        family_rates=FamilyRateScales.OVERSEAS.value,
        dependants_counted_at_most=None,
    )
    """From 1/10/2025."""
