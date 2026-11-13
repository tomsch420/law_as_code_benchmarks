"""
Tests of the eligibility for the personal housing aids.
"""

from __future__ import annotations

import datetime
from fractions import Fraction

from law_as_code_benchmarks.catala.domain import SchoolingStage, Territory
from law_as_code_benchmarks.catala.entitlement import (
    FamilyBenefitEntitlementProvision,
)
from law_as_code_benchmarks.catala.housing.domain import (
    FamilyRightHolder,
    Foreign,
    ForeignerConditions,
    HomeBuyer,
    HomeOwner,
    Kinship,
    Loan,
    LoanHolder,
    LoanType,
    Married,
    NewBuilding,
    NoFinancingAgreement,
    AcquisitionWorks,
    OtherDependant,
    OtherDependentPerson,
    OwnershipWorks,
    Single,
)
from law_as_code_benchmarks.catala.housing.eligibility import (
    ChildAgeLimitProvision,
    CommonEligibilityCase,
    CountedDependantsProvision,
    ElderlyAscendantConditionProvision,
    EligibilityOutput,
    HousingAllowanceEligibilityCase,
    HousingAllowanceType,
    LoanConditionProvision,
    NationalityConditionProvision,
    OccupancyConditionProvision,
    PersonalisedAidEligibilityCase,
    PersonalisedAidEligibilityProvision,
    RetirementAgeProvision,
    SurfaceConditionProvision,
)
from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.reader import Duration

from .housings import (
    applicant_born,
    dependent_child,
    dwelling_of,
    housing_household,
    social_tenancy,
)

# %% helpers


def common_case(
    assessment_date: datetime.date = datetime.date(2022, 5, 1), **household: object
) -> CommonEligibilityCase:
    """:return: The common conditions for a household built from *household*, assessed on *assessment_date*."""
    return CommonEligibilityCase(
        household=housing_household(**household),
        applicant=applicant_born(),
        assessment_date=assessment_date,
    )


def home_buyer(signature_date: datetime.date) -> HomeBuyer:
    """:return: A buyer of a new home with an ordinary loan the applicant signed on *signature_date*."""
    return HomeBuyer(
        owner=HomeOwner(
            monthly_repayment=Money.from_euros(800),
            monthly_loan_charges=Money.zero,
            entry_date=signature_date,
            acquisition_works=AcquisitionWorks.NO_WORKS,
            ownership_works=OwnershipWorks.NO_WORKS,
            first_occupation_by_beneficiary=True,
            co_ownership=False,
            situation_r822_11_13_17=False,
            building_age=NewBuilding(),
            loan=Loan(
                loan_type=LoanType.OTHER,
                signature_date=signature_date,
                holder=LoanHolder.APPLICANT,
                overseas_financing_agreement=NoFinancingAgreement(),
            ),
            state_aided_social_scalable_housing=False,
        )
    )


def ascendant_born(birth_date: datetime.date, resources: Money) -> OtherDependant:
    """:return: A parent of the applicant born on *birth_date*, neither disabled nor holding an allowance."""
    return OtherDependant(
        person=OtherDependentPerson(
            birth_date=birth_date,
            resources=resources,
            related_up_to_third_degree=True,
            kinship=Kinship.ASCENDANT,
            disabled_or_restricted_from_work=False,
            beneficiary_l161_19_l351_8_l643_3=False,
            old_age_allowance_holder=False,
        )
    )


# %% surface


def test_the_surface_asked_grows_by_nine_square_metres_for_each_other_person() -> None:
    """
    R822-25: a person alone with two children needs 9 m² and 9 more for each child; a
    square metre less fails the condition.
    """
    asked = (
        SurfaceConditionProvision.surface_per_adult_count[1]
        + 2 * SurfaceConditionProvision.surface_per_other_person
    )
    children = [dependent_child(datetime.date(2015, 1, 1))] * 2
    holds = [
        common_case(
            dependants=children,
            family_situation=Single(),
            dwelling=dwelling_of(surface_square_metres=surface),
        )
        .sole_conclusion(SurfaceConditionProvision)
        .holds
        for surface in (asked, asked - 1)
    ]
    assert holds == [True, False]


def test_the_surface_asked_stops_at_seventy_square_metres_for_eight_persons() -> None:
    """
    R822-25: a couple with seven other occupants needs no more than 70 m².
    """
    case = common_case(
        other_occupants=7,
        dwelling=dwelling_of(
            surface_square_metres=SurfaceConditionProvision.largest_surface_asked
        ),
    )
    assert case.sole_conclusion(SurfaceConditionProvision).holds


def test_mayotte_asks_less_surface_of_a_couple() -> None:
    """
    R861-5: a couple in Mayotte needs 13 m², where 16 are asked elsewhere.
    """
    surface = SurfaceConditionProvision.mayotte_surface_per_adult_count[2]
    holds = [
        common_case(
            residence=residence,
            dwelling=dwelling_of(surface_square_metres=surface),
        )
        .sole_conclusion(SurfaceConditionProvision)
        .holds
        for residence in (Territory.MAYOTTE, Territory.METROPOLITAN_FRANCE)
    ]
    assert holds == [True, False]


# %% nationality and occupancy


def test_a_foreigner_must_meet_the_conditions_of_the_social_security_code() -> None:
    """
    L822-2: a foreigner not meeting L512-2 of the Code de la sécurité sociale fails the
    condition.
    """
    case = CommonEligibilityCase(
        household=housing_household(),
        applicant=applicant_born(
            nationality=Foreign(
                conditions=ForeignerConditions(
                    meets_l512_2=False, meets_mayotte_ordinance_article_4=True
                )
            )
        ),
        assessment_date=datetime.date(2022, 5, 1),
    )
    assert not case.sole_conclusion(NationalityConditionProvision).holds


def test_mayotte_excludes_a_french_applicant_as_catala_reads_it() -> None:
    """
    L861-5: in Mayotte the nationality condition holds only for a foreigner meeting the
    ordinance of 2002.
    """
    case = common_case(residence=Territory.MAYOTTE)
    assert not case.sole_conclusion(NationalityConditionProvision).holds


def test_a_family_share_of_the_dwelling_excludes_a_tenant_from_its_threshold() -> None:
    """
    L822-3 and R822-1: the family owning a share below 10 % keeps the right, a share of
    10 % excludes it.
    """
    threshold = OccupancyConditionProvision.ownership_threshold
    holds = [
        common_case(dwelling=dwelling_of(owner=FamilyRightHolder(share=share)))
        .sole_conclusion(OccupancyConditionProvision)
        .holds
        for share in (threshold - Fraction(1, 100), threshold)
    ]
    assert holds == [True, False]


# %% persons in the household's charge


def test_the_age_limit_of_a_child_is_21_from_september_2019_and_22_overseas() -> None:
    """
    R823-4 and D861-9: 21 from September 2019, 22 overseas; R512-2's before.
    """
    ages = [
        common_case(assessment_date=day, residence=residence)
        .sole_conclusion(ChildAgeLimitProvision)
        .age
        for day, residence in (
            (datetime.date(2019, 9, 1), Territory.METROPOLITAN_FRANCE),
            (datetime.date(2019, 8, 31), Territory.METROPOLITAN_FRANCE),
            (datetime.date(2019, 8, 31), Territory.REUNION),
        )
    ]
    assert ages == [
        ChildAgeLimitProvision.age_limit,
        None,
        ChildAgeLimitProvision.overseas_age_limit,
    ]


def test_a_child_of_20_after_compulsory_schooling_counts_until_21() -> None:
    """
    R823-4: a child past compulsory schooling who earns nothing counts at 20, an age
    R512-2 alone would exclude.
    """
    child = dependent_child(datetime.date(2001, 6, 1), SchoolingStage.AFTER)
    case = common_case(
        assessment_date=datetime.date(2022, 5, 1),
        dependants=[child],
    )
    assert FamilyBenefitEntitlementProvision.age_limit < 21
    assert case.sole_conclusion(CountedDependantsProvision).dependants == [child]
    assert case.output(EligibilityOutput.DEPENDANT_COUNT) == 1


def test_a_foreign_child_not_meeting_the_conditions_counts_only_in_mayotte() -> None:
    """
    L823-1, seventh paragraph: such a child does not count, but in Mayotte, where L861-5
    sets the paragraph aside.
    """
    child = dependent_child(
        datetime.date(2015, 1, 1),
        nationality=Foreign(
            conditions=ForeignerConditions(
                meets_l512_2=False, meets_mayotte_ordinance_article_4=False
            )
        ),
    )
    counted = [
        common_case(dependants=[child], residence=residence).output(
            EligibilityOutput.DEPENDANT_COUNT
        )
        for residence in (Territory.METROPOLITAN_FRANCE, Territory.MAYOTTE)
    ]
    assert counted == [0, 1]


def test_an_ascendant_past_the_full_rate_age_with_small_resources_counts() -> None:
    """
    R823-4 2°: before September 2023, an ascendant five years past the applicant's
    pension age, with resources within 125 % of the individual ceiling, counts.
    """
    retirement = RetirementAgeProvision.age_before_2023
    birth = datetime.date(2022 - retirement.years - 5, 1, 1)
    ascendant = ascendant_born(birth, Money.from_euros(1000))
    case = common_case(dependants=[ascendant])
    assert case.sole_conclusion(ElderlyAscendantConditionProvision).holds
    assert case.output(EligibilityOutput.DEPENDANT_COUNT) == 1


def test_the_pension_age_follows_the_birth_date_and_the_2023_reform() -> None:
    """
    D161-2-1-9: 61 years and 2 months for one born in 1953; L161-17-2: 64 for one born
    from 1968 after the reform.
    """
    ages = []
    for birth, day in (
        (datetime.date(1953, 3, 1), datetime.date(2022, 5, 1)),
        (datetime.date(1970, 5, 2), datetime.date(2024, 5, 1)),
    ):
        case = CommonEligibilityCase(
            household=housing_household(),
            applicant=applicant_born(birth),
            assessment_date=day,
        )
        ages.append(case.sole_conclusion(RetirementAgeProvision).age)
    assert ages == [Duration(years=61, months=2), Duration(years=64)]


# %% the personalised housing aid


def test_a_social_landlord_without_agreement_gives_no_personalised_aid() -> None:
    """
    L831-1: a dwelling let by a social landlord not under agreement is not covered.
    """
    eligible = [
        PersonalisedAidEligibilityCase(
            household=housing_household(
                dwelling=dwelling_of(occupancy=social_tenancy(agreed=agreed))
            ),
            applicant=applicant_born(),
            assessment_date=datetime.date(2022, 5, 1),
        ).output(EligibilityOutput.ELIGIBILITY)
        for agreed in (True, False)
    ]
    assert eligible == [True, False]


def test_a_home_bought_with_a_loan_signed_from_the_end_of_2017_gives_no_personalised_aid() -> (
    None
):
    """
    L831-2: a loan signed from December 31, 2017 excludes the personalised aid.
    """
    case = PersonalisedAidEligibilityCase(
        household=housing_household(
            dwelling=dwelling_of(
                occupancy=home_buyer(LoanConditionProvision.first_excluded_signature)
            )
        ),
        applicant=applicant_born(),
        assessment_date=datetime.date(2022, 5, 1),
    )
    assert not case.sole_conclusion(LoanConditionProvision).holds
    assert not case.output(EligibilityOutput.ELIGIBILITY)


def test_saint_pierre_and_miquelon_has_no_personalised_aid_from_2021() -> None:
    """
    L860-3: no personalised aid in Saint-Pierre-et-Miquelon from January 1, 2021.
    """
    eligible = [
        PersonalisedAidEligibilityCase(
            household=housing_household(residence=Territory.SAINT_PIERRE_AND_MIQUELON),
            applicant=applicant_born(),
            assessment_date=day,
        )
        .sole_conclusion(PersonalisedAidEligibilityProvision)
        .holds
        for day in (
            PersonalisedAidEligibilityProvision.first_day_of_l860_3,
            PersonalisedAidEligibilityProvision.first_day_of_l860_3
            - datetime.timedelta(days=1),
        )
    ]
    assert eligible == [False, True]


# %% the housing allowances


def allowance_case(
    applicant_birth: datetime.date = datetime.date(1970, 5, 2),
    receives_personalised_aid: bool = False,
    hosted_in_care_unit: bool = False,
    **household: object,
) -> HousingAllowanceEligibilityCase:
    """:return: The eligibility for the allowances of a household built from *household*, on May 1, 2022."""
    return HousingAllowanceEligibilityCase(
        household=housing_household(**household),
        applicant=applicant_born(
            applicant_birth, hosted_in_care_unit=hosted_in_care_unit
        ),
        assessment_date=datetime.date(2022, 5, 1),
        receives_personalised_aid=receives_personalised_aid,
    )


def test_a_couple_married_for_less_than_five_years_gets_the_family_allowance() -> None:
    """
    L841-1 3° and D841-1: married within five years, without a child giving no right;
    the social one after.
    """
    allowances = [
        allowance_case(family_situation=Married(wedding_date=wedding)).output(
            EligibilityOutput.ELIGIBILITY
        )
        for wedding in (datetime.date(2018, 1, 1), datetime.date(2017, 1, 1))
    ]
    assert allowances == [HousingAllowanceType.FAMILY, HousingAllowanceType.SOCIAL]


def test_a_household_receiving_the_personalised_aid_gets_no_allowance() -> None:
    """
    L841-2: the personalised aid excludes the allowances.
    """
    case = allowance_case(receives_personalised_aid=True)
    assert (
        case.output(EligibilityOutput.ELIGIBILITY) == HousingAllowanceType.NOT_ELIGIBLE
    )


def test_an_applicant_in_a_long_term_care_unit_gets_the_social_allowance() -> None:
    """
    L841-3: the social allowance, whatever L841-1 would give.
    """
    case = allowance_case(
        hosted_in_care_unit=True,
        family_situation=Married(wedding_date=datetime.date(2021, 1, 1)),
    )
    assert case.output(EligibilityOutput.ELIGIBILITY) == HousingAllowanceType.SOCIAL


def test_a_home_bought_with_a_loan_signed_after_2017_gets_no_allowance() -> None:
    """
    L841-4: no allowance for a home bought with a loan signed after December 31, 2017.
    """
    case = allowance_case(
        dwelling=dwelling_of(occupancy=home_buyer(datetime.date(2018, 1, 1)))
    )
    assert (
        case.output(EligibilityOutput.ELIGIBILITY) == HousingAllowanceType.NOT_ELIGIBLE
    )
