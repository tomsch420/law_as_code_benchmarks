"""
Tests of the housing aids of homes bought and residence halls, and of the calculator.
"""

from __future__ import annotations

import datetime
from fractions import Fraction

import pytest

from law_as_code_benchmarks.catala.domain import Territory
from law_as_code_benchmarks.catala.housing.calculator import (
    AllowanceComputationCase,
    PersonalisedAidComputationCase,
)
from law_as_code_benchmarks.catala.housing.domain import (
    AcquisitionWorks,
    Cohabiting,
    HomeBuyer,
    HomeOwner,
    HousingZone,
    Loan,
    LoanHolder,
    LoanType,
    NewBuilding,
    NoFinancingAgreement,
    OwnershipWorks,
    ResidenceHall,
    ResidenceHallRentCategory,
    ResidenceHallResident,
    ResidenceHallType,
)
from law_as_code_benchmarks.catala.housing.household_tables import (
    AllowancePaymentCeiling,
    HouseholdTable,
    PersonalisedAidPaymentCeiling,
    ResidenceHallCeilings,
    ResidenceHallRentEquivalence,
)
from law_as_code_benchmarks.catala.housing.ownership import (
    OwnershipAidCase,
    OwnershipAidOutput,
    OwnershipAllowanceCase,
    RepaymentCeilingProvision,
    ThresholdedResourcesProvision,
)
from law_as_code_benchmarks.catala.housing.rented import (
    AidFamilySituation,
    AidType,
    RentedAllowanceCase,
)
from law_as_code_benchmarks.catala.housing.residence_hall import (
    CoverageRounding,
    HallAidCase,
    HallParts,
    HallPartsCase,
    HallPartsOutput,
    HallPartsProvision,
    MinimumRentEquivalenceCase,
    MinimumRentEquivalenceOutput,
    MinimumRentEquivalenceProvision,
    PartsTables,
    SecondCaseProvision,
)
from law_as_code_benchmarks.catala.money import Money

# %% tables


def months(first: datetime.date, last: datetime.date) -> list[datetime.date]:
    """:return: The first day of each month from *first* to *last*."""
    days = []
    day = first
    while day <= last:
        days.append(day)
        day = (day.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
    return days


def test_one_residence_hall_ceiling_and_rent_equivalence_is_in_force_each_month() -> (
    None
):
    """
    Articles 27 and 43: from October 2020 to 2027, one version each month, one
    equivalence per category.
    """
    for day in months(datetime.date(2020, 10, 1), datetime.date(2027, 12, 1)):
        ceilings = [
            version
            for version in ResidenceHallCeilings.versions()
            if version.period.contains(day)
        ]
        equivalences = [
            version.category
            for version in ResidenceHallRentEquivalence.versions()
            if version.period.contains(day)
        ]
        assert len(ceilings) == 1, day
        assert sorted(equivalences) == sorted(ResidenceHallRentCategory), day


def test_the_allowance_payment_ceilings_follow_each_other_from_1992() -> None:
    """
    Article 33: each row starts the day the one before ends, the last open-ended.
    """
    rows = AllowancePaymentCeiling.rows()
    assert [row.computed_from for row in rows[1:]] == [
        row.computed_before for row in rows[:-1]
    ]
    assert rows[-1].computed_before is None


def test_every_personalised_aid_payment_ceiling_names_its_loans() -> None:
    """
    Articles 17 and 18: each row holds for loans of D331-32 or D331-63 and D331-64.
    """
    assert {
        loan for row in PersonalisedAidPaymentCeiling.rows() for loan in row.loan_types
    } == {LoanType.ARTICLE_D331_32, LoanType.ARTICLES_D331_63_64}


def test_an_amount_beyond_those_listed_adds_to_the_amount_catala_sets_apart() -> None:
    """
    Article 33 sets the amount further dependants add to apart from the last one listed,
    sometimes differing.
    """
    table = HouseholdTable(
        single=Money(cents=1),
        couple=Money(cents=2),
        by_dependants=(Money(cents=10), Money(cents=20)),
        beyond_listed=Money(cents=21),
        each_further_dependant=Money(cents=5),
    )
    assert [table.amount_for(True, count) for count in (0, 2, 3)] == [
        Money(cents=2),
        Money(cents=20),
        Money(cents=26),
    ]


# %% residence halls


def test_the_flat_amount_of_the_second_case_is_not_multiplied_by_the_parts() -> None:
    """
    D832-26: without resources, an ordinary hall's flat amount counts by part, that of
    the 2° once.
    """
    amounts = [
        MinimumRentEquivalenceCase(
            assessment_date=datetime.date(2022, 3, 1),
            resources=Money.zero,
            second_case_of_d832_25=second_case,
            parts=Fraction(2),
        ).output(MinimumRentEquivalenceOutput.AMOUNT)
        for second_case in (False, True)
    ]
    assert amounts == [
        Money.from_exact_units(
            Fraction(MinimumRentEquivalenceProvision.ordinary_flat_amount.cents, 100)
            * 2
            / 12
        ),
        Money.from_exact_units(
            Fraction(MinimumRentEquivalenceProvision.second_case_flat_amount.cents, 100)
            / 12
        ),
    ]


def test_overseas_limits_the_parts_of_dependants_until_april_2023() -> None:
    """
    D861-8: one part at most for the dependants beyond four, past six of them.
    """
    table = PartsTables.ORDINARY.value
    parts = [
        HallPartsCase(
            assessment_date=day,
            second_case_of_d832_25=False,
            dependant_count=8,
            family_situation=AidFamilySituation.COUPLE,
            limits_dependant_parts=True,
        ).output(HallPartsOutput.PARTS)
        for day in (datetime.date(2022, 3, 1), datetime.date(2023, 4, 5))
    ]
    assert parts == [
        table.by_dependants[-1] + HallPartsProvision.limited_addition,
        table.by_dependants[-1] + table.each_further_dependant * 4,
    ]


def hall_case(
    hall_type: ResidenceHallType,
    agreement_date: datetime.date,
    residence: Territory = Territory.METROPOLITAN_FRANCE,
    assessment_date: datetime.date = datetime.date(2022, 3, 1),
) -> HallAidCase:
    """:return: A couple without dependants in a zone 2 hall of *hall_type*, with 15,000 € of resources and a fee of 400 €."""
    return HallAidCase(
        residence=residence,
        young_workers_hostel=False,
        hall_type=hall_type,
        agreement_date=agreement_date,
        resources=Money.from_euros(15000),
        dependant_count=0,
        family_situation=AidFamilySituation.COUPLE,
        zone=HousingZone.ZONE_2,
        assessment_date=assessment_date,
        fee=Money.from_euros(400),
    )


def test_a_social_residence_agreed_from_1995_is_of_the_second_case_but_overseas_from_april_2023() -> (
    None
):
    """
    D832-25 2° and D861-21.
    """
    agreed = SecondCaseProvision.first_social_residence_agreement
    holds = [
        hall_case(
            ResidenceHallType.SOCIAL_RESIDENCE, agreed, residence, day
        ).second_case
        for residence, day in (
            (Territory.METROPOLITAN_FRANCE, datetime.date(2023, 6, 1)),
            (Territory.REUNION, SecondCaseProvision.first_day_of_d861_21),
        )
    ]
    assert holds == [True, False]


def test_a_coverage_is_rounded_down_to_the_hundredth_and_capped() -> None:
    """
    D832-25: rounded down to the hundredth, at most its maximum.
    """
    assert CoverageRounding.rounded(Fraction(41_99, 10_000), Fraction(95, 100)) == (
        Fraction(41, 100)
    )
    assert CoverageRounding.rounded(Fraction(97, 100), Fraction(95, 100)) == (
        Fraction(95, 100)
    )


# %% homes bought


def ownership_inputs(**overrides: object) -> dict[str, object]:
    """:return: A couple with two dependants in zone 2 repaying 650 € of a loan signed on December 15, 2017, by default."""
    return {
        "monthly_repayment": Money.from_euros(650),
        "resources": Money.from_euros(18000),
        "dependant_count": 2,
        "family_situation": AidFamilySituation.COUPLE,
        "loan_signature_date": datetime.date(2017, 12, 15),
        "first_occupation_by_beneficiary": False,
        "entry_date": datetime.date(2017, 12, 15),
        "co_ownership": False,
        "situation_r822_11_13_17": False,
        "zone": HousingZone.ZONE_2,
        "assessment_date": datetime.date(2022, 5, 1),
        "residence": Territory.METROPOLITAN_FRANCE,
    } | overrides


def personalised_ownership_case(**overrides: object) -> OwnershipAidCase:
    """:return: The personalised aid of a new home bought with a loan of D331-63 and D331-64, without works."""
    return OwnershipAidCase(
        **ownership_inputs(**overrides),
        acquisition_works=AcquisitionWorks.NO_WORKS,
        loan_type=LoanType.ARTICLES_D331_63_64,
        building_age=NewBuilding(),
    )


def test_a_co_owned_home_has_three_quarters_of_the_ceiling() -> None:
    """
    Article 24: 75 % of the ceiling in a co-owned building.
    """
    ceilings = [
        personalised_ownership_case(co_ownership=co_owned)
        .sole_conclusion(RepaymentCeilingProvision)
        .amount
        for co_owned in (False, True)
    ]
    assert ceilings[1] == ceilings[0] * RepaymentCeilingProvision.co_ownership_share


def test_the_first_occupant_has_the_higher_ceiling_of_signature_and_entry() -> None:
    """
    D832-14: the entry's ceiling where it is higher than the signature's.
    """
    signed_early = dict(
        loan_signature_date=datetime.date(2016, 1, 1),
        entry_date=datetime.date(2020, 1, 1),
    )
    ceilings = [
        personalised_ownership_case(
            **signed_early, first_occupation_by_beneficiary=first
        )
        .sole_conclusion(RepaymentCeilingProvision)
        .amount
        for first in (False, True)
    ]
    assert ceilings[1] > ceilings[0]


def test_a_loan_no_row_covers_gives_no_aid() -> None:
    """
    Articles 17 and 18 set no ceiling for an ordinary loan: Catala's example computes
    nothing.
    """
    case = OwnershipAidCase(
        **ownership_inputs(),
        acquisition_works=AcquisitionWorks.NO_WORKS,
        loan_type=LoanType.OTHER,
        building_age=NewBuilding(),
    )
    assert case.output(OwnershipAidOutput.ELIGIBLE_REPAYMENT) is None


def test_small_resources_are_raised_to_the_threshold_rounded_up_to_the_hundred() -> (
    None
):
    """
    D842-12: 16.25 times the repayment, and 49.99 €, at 1 %, rounded, times a hundred.
    """
    case = OwnershipAllowanceCase(
        **ownership_inputs(resources=Money.from_euros(5000)),
        ownership_works=OwnershipWorks.NO_WORKS,
        monthly_loan_charges=Money.zero,
        state_aided_social_scalable_housing=False,
    )
    threshold = Money.from_euros(650) * ThresholdedResourcesProvision.repayment_multiple
    assert case.thresholded_resources == (
        ((threshold + Money(cents=4999)) * Fraction(1, 100)).rounded_to_units() * 100
    )


# %% the computation whatever the dwelling


def hall_resident() -> ResidenceHallResident:
    """:return: A resident of a social residence agreed in 2000, paying a fee of 400 €."""
    return ResidenceHallResident(
        hall=ResidenceHall(
            hall_type=ResidenceHallType.SOCIAL_RESIDENCE,
            young_workers_hostel=False,
            meets_r832_21=True,
            agreed_under_book_iii_title_v_chapter_iii=True,
            agreed_under_overseas_rules=False,
            agreement_date=datetime.date(2000, 1, 1),
            built_under_1957_law=False,
            fee=Money.from_euros(400),
            rent_equivalence_category=ResidenceHallRentCategory.OTHER_PERSONS,
            disability_aid_recipient=False,
            furnished_d842_2=False,
            is_room=False,
            is_house_share=False,
        )
    )


@pytest.mark.parametrize(
    "resources, rounded",
    [(Money(cents=1999950), 2000000), (Money(cents=2000000), 2000000)],
)
def test_the_resources_are_rounded_up_to_the_hundred(
    resources: Money, rounded: int
) -> None:
    """
    D823-17 4°: the resources rounded up to the hundred euros.
    """
    case = PersonalisedAidComputationCase(
        occupancy=hall_resident(),
        resources=resources,
        family_situation=Cohabiting(),
        dependant_count=0,
        zone=HousingZone.ZONE_2,
        assessment_date=datetime.date(2022, 3, 1),
        aid_type=AidType.PERSONALISED_AID,
        residence=Territory.METROPOLITAN_FRANCE,
    )
    assert case.rounded_resources == Money(cents=rounded)


def test_saint_pierre_computes_a_residence_hall_allowance_as_a_rented_home() -> None:
    """
    D863-7: the fee taken as the rent of a rented home.
    """
    case = AllowanceComputationCase(
        occupancy=hall_resident(),
        resources=Money.from_euros(12000),
        family_situation=Cohabiting(),
        dependant_count=0,
        zone=HousingZone.ZONE_2,
        assessment_date=datetime.date(2023, 4, 1),
        aid_type=AidType.SOCIAL_ALLOWANCE,
        residence=Territory.SAINT_PIERRE_AND_MIQUELON,
    )
    assert isinstance(case.sector, RentedAllowanceCase)
    assert case.sector.rent == Money.from_euros(400)


def test_a_home_bought_gets_the_allowance_of_homes_bought() -> None:
    """
    D823-9: the computation of the sector of the dwelling.
    """
    buyer = HomeBuyer(
        owner=HomeOwner(
            monthly_repayment=Money.from_euros(450),
            monthly_loan_charges=Money.from_euros(450),
            entry_date=datetime.date(2015, 10, 10),
            acquisition_works=AcquisitionWorks.NO_WORKS,
            ownership_works=OwnershipWorks.NO_WORKS,
            first_occupation_by_beneficiary=False,
            co_ownership=False,
            situation_r822_11_13_17=False,
            building_age=NewBuilding(),
            loan=Loan(
                loan_type=LoanType.OTHER,
                signature_date=datetime.date(2015, 10, 1),
                holder=LoanHolder.APPLICANT,
                overseas_financing_agreement=NoFinancingAgreement(),
            ),
            state_aided_social_scalable_housing=False,
        )
    )
    case = AllowanceComputationCase(
        occupancy=buyer,
        resources=Money.from_euros(17500),
        family_situation=Cohabiting(),
        dependant_count=2,
        zone=HousingZone.ZONE_2,
        assessment_date=datetime.date(2023, 3, 15),
        aid_type=AidType.FAMILY_ALLOWANCE,
        residence=Territory.GUADELOUPE,
    )
    assert isinstance(case.sector, OwnershipAllowanceCase)
    assert case.sector.monthly_loan_charges == Money.from_euros(450)
