"""
Tests of the personal housing aids of a rented home.
"""

from __future__ import annotations

import datetime
from fractions import Fraction

import pytest

from law_as_code_benchmarks.catala.domain import Territory
from law_as_code_benchmarks.catala.housing.domain import (
    HousingZone,
    MoveDetails,
    Moved,
    NotMoved,
)
from law_as_code_benchmarks.catala.housing.rented import (
    AidFamilySituation,
    AidTreatment,
    AidType,
    ContributionRoundedAidProvision,
    FurnishedRentProvision,
    IncomeAbatementProvision,
    MinimumAidProvision,
    RentCeilingProvision,
    RentedAidCase,
    RentedAidOutput,
    RentedAllowanceCase,
    SaintPierrePhasedAidProvision,
    ScaledDependantsProvision,
)
from law_as_code_benchmarks.catala.housing.rented_scales import (
    IncomeAbatements,
    IncomeAbatementScales,
    MayotteAbatementScales,
    OverseasScales,
    RentedHomeScales,
)
from law_as_code_benchmarks.catala.money import Money

# %% helpers


def case_inputs(
    assessment_date: datetime.date = datetime.date(2022, 3, 1),
    dependant_count: int = 0,
    residence: Territory = Territory.METROPOLITAN_FRANCE,
    rent: Money = Money.from_euros(500),
    aid_type: AidType = AidType.PERSONALISED_AID,
    is_room: bool = False,
    furnished: bool = False,
) -> dict[str, object]:
    """:return: The inputs of a person alone renting in zone 2, with 9,000 € of resources, by default on March 1, 2022."""
    return dict(
        rent=rent,
        resources=Money.from_euros(9000),
        disability_aid_recipient=False,
        assessment_date=assessment_date,
        dependant_count=dependant_count,
        family_situation=AidFamilySituation.SINGLE,
        zone=HousingZone.ZONE_2,
        is_room=is_room,
        paying_guests_elderly_or_disabled=False,
        aid_type=aid_type,
        is_house_share=False,
        solidarity_rent_reduction=Money.zero,
        furnished_d842_2=furnished,
        residence=residence,
    )


def rented_case(**inputs: object) -> RentedAidCase:
    """:return: The personalised aid of :func:`case_inputs` built from *inputs*."""
    return RentedAidCase(**case_inputs(**inputs))


# %% the scales in force


@pytest.mark.parametrize(
    "scales, first_day",
    [
        (RentedHomeScales, datetime.date(2020, 10, 1)),
        (IncomeAbatementScales, datetime.date(2020, 1, 1)),
        (OverseasScales, datetime.date(2020, 10, 1)),
    ],
)
def test_exactly_one_scale_is_in_force_each_month(
    scales: type, first_day: datetime.date
) -> None:
    """
    From the first version Catala's example states to 2027, each month has exactly one
    version in force.
    """
    day = first_day
    while day < datetime.date(2028, 1, 1):
        in_force = [member for member in scales if member.value.period.contains(day)]
        assert len(in_force) == 1, day
        day = (day.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)


def test_no_aid_is_computed_before_october_2020() -> None:
    """
    Catala's example asserts the day is from October 1, 2020: nothing is concluded
    before.
    """
    case = rented_case(assessment_date=datetime.date(2020, 9, 30))
    assert case.output(RentedAidOutput.INITIAL_AID) is None


# %% ceilings and rents


def test_a_room_has_its_own_ceiling() -> None:
    """
    Article 8: the ceiling of a room, whatever the household.
    """
    case = rented_case(is_room=True, dependant_count=3)
    assert (
        case.sole_conclusion(RentCeilingProvision).amount
        == RentedHomeScales.OCTOBER_2021.value.room_ceiling.zone_2
    )


def test_the_ceiling_grows_with_each_dependant_after_the_first() -> None:
    """
    Article 7: the ceiling of one dependant, and more for each further one.
    """
    ceilings = RentedHomeScales.OCTOBER_2021.value.ceilings
    case = rented_case(dependant_count=3)
    assert case.sole_conclusion(RentCeilingProvision).amount == (
        ceilings.one_dependant.zone_2 + ceilings.each_further_dependant.zone_2 * 2
    )


def test_overseas_scales_count_six_dependants_at_most_until_2022() -> None:
    """
    Article 46: until 2022, the overseas scales count six of eight dependants; from 2023
    all.
    """
    counts = [
        rented_case(assessment_date=day, dependant_count=8, residence=Territory.REUNION)
        .sole_conclusion(ScaledDependantsProvision)
        .count
        for day in (datetime.date(2022, 3, 1), datetime.date(2023, 3, 1))
    ]
    assert counts == [
        OverseasScales.JANUARY_2022.value.dependants_counted_at_most,
        8,
    ]


def test_a_furnished_dwelling_counts_two_thirds_of_its_rent() -> None:
    """
    D842-2: two thirds of the rent, rounded to the cent.
    """
    case = rented_case(furnished=True, rent=Money.from_euros(500))
    assert case.sole_conclusion(FurnishedRentProvision).amount == (
        Money.from_euros(500) * FurnishedRentProvision.furnished_share
    )


# %% abatements


def test_the_abatement_grows_beyond_six_dependants() -> None:
    """
    Article 15: the abatement of six dependants, and more for each further one.
    """
    abatements = IncomeAbatementScales.JANUARY_2022.value
    case = rented_case(dependant_count=8)
    assert case.sole_conclusion(IncomeAbatementProvision).amount == (
        abatements.by_dependants[-1] + abatements.each_further_dependant * 2
    )


def test_overseas_has_its_own_abatement_for_one_dependant() -> None:
    """
    Article 46: the abatement of one dependant overseas.
    """
    case = rented_case(dependant_count=1, residence=Territory.GUADELOUPE)
    assert (
        case.sole_conclusion(IncomeAbatementProvision).amount
        == OverseasScales.JANUARY_2022.value.one_dependant_abatement
    )


def test_mayotte_has_its_own_abatements_in_2021() -> None:
    """
    Article 47: Mayotte's abatements in 2021, the one of six dependants holding beyond.
    """
    case = rented_case(
        assessment_date=datetime.date(2021, 3, 1),
        dependant_count=7,
        residence=Territory.MAYOTTE,
    )
    abatements: IncomeAbatements = MayotteAbatementScales.JANUARY_2021.value
    assert (
        case.sole_conclusion(IncomeAbatementProvision).amount
        == abatements.by_dependants[-1]
    )


# %% the treatment of the aid


def test_saint_pierre_pays_no_contribution_on_the_aid() -> None:
    """
    LO6414-1: the aid is rounded down to the euro, no contribution taken.
    """
    case = rented_case(residence=Territory.SAINT_PIERRE_AND_MIQUELON)
    treatment = AidTreatment(case=case, aid=Money(cents=36948 + 500))
    assert treatment.sole_amount(ContributionRoundedAidProvision) == Money.from_euros(
        369
    )


def test_saint_pierre_phases_the_aid_in_by_eighths_until_2026() -> None:
    """
    Décret n° 2021-1750, article 7: five eighths of the aid in 2023.
    """
    case = rented_case(
        assessment_date=datetime.date(2023, 4, 1),
        residence=Territory.SAINT_PIERRE_AND_MIQUELON,
    )
    treatment = AidTreatment(case=case, aid=Money.from_euros(380))
    before = treatment.sole_amount(ContributionRoundedAidProvision)
    assert treatment.sole_amount(SaintPierrePhasedAidProvision) == before * (
        1 - Fraction(SaintPierrePhasedAidProvision.full_year - 2023, 8)
    )


def test_an_allowance_below_ten_euros_is_not_paid() -> None:
    """
    Article 12: no allowance below 10 €; the personalised aid has no least amount.
    """
    amounts = [
        AidTreatment(
            case=rented_case(aid_type=aid_type), aid=Money.from_euros(14)
        ).sole_amount(MinimumAidProvision)
        for aid_type in (AidType.FAMILY_ALLOWANCE, AidType.PERSONALISED_AID)
    ]
    assert amounts[0] == Money.zero
    assert amounts[1] > Money.zero


def test_a_household_moving_to_a_dearer_dwelling_keeps_its_previous_allowance() -> None:
    """
    D842-4: the rent less the previous rent net of the previous allowance, untreated.
    """
    details = MoveDetails(
        previous_rent=Money.from_euros(450),
        previous_housing_allowance=Money.from_euros(200),
    )
    case = RentedAllowanceCase(
        **case_inputs(rent=Money.from_euros(500), aid_type=AidType.FAMILY_ALLOWANCE),
        home_change=Moved(details=details),
    )
    assert case.output(RentedAidOutput.INITIAL_AID) == Money.from_euros(250)
    assert case.treated_aid(Money.from_euros(250)) == Money.from_euros(250)


def test_a_household_that_did_not_move_gets_the_allowance_on_the_aid_scale() -> None:
    """
    D842-1: the allowance is the personalised aid's computation.
    """
    base = rented_case(aid_type=AidType.FAMILY_ALLOWANCE)
    case = RentedAllowanceCase(
        **case_inputs(aid_type=AidType.FAMILY_ALLOWANCE), home_change=NotMoved()
    )
    assert case.output(RentedAidOutput.INITIAL_AID) == base.output(
        RentedAidOutput.INITIAL_AID
    )
