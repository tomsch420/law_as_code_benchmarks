"""
Households, dwellings and applicants the tests of the housing aids share.
"""

from __future__ import annotations

import datetime

from law_as_code_benchmarks.catala.domain import SchoolingStage, Territory
from law_as_code_benchmarks.catala.housing.domain import (
    Applicant,
    ChildDependant,
    Cohabiting,
    Dependant,
    DependentChild,
    Dwelling,
    FamilySituation,
    French,
    HousingHousehold,
    HousingZone,
    Nationality,
    NoSharedResidence,
    NotMoved,
    NotSublet,
    Occupancy,
    OtherRightHolder,
    RightHolder,
    SocialLandlord,
    SocialLandlordAgreement,
    Tenancy,
    Tenant,
)
from law_as_code_benchmarks.catala.money import Money

# %% dwellings


def social_tenancy(agreed: bool = True) -> Tenant:
    """:return: A tenancy of 500 € a month from a social landlord, under agreement unless said otherwise."""
    return Tenant(
        tenancy=Tenancy(
            landlord=SocialLandlord(
                agreement=SocialLandlordAgreement(
                    agreed_under_book_iii_title_v_chapter_iii=agreed,
                    solidarity_rent_reduction=Money.zero,
                )
            ),
            rent=Money.from_euros(500),
            disability_aid_recipient=False,
            is_room=False,
            is_house_share=False,
            paying_guests_elderly_or_disabled=False,
            furnished_d842_2=False,
            home_change=NotMoved(),
        )
    )


def dwelling_of(
    occupancy: Occupancy | None = None,
    surface_square_metres: int = 80,
    owner: RightHolder | None = None,
    usufructuary: RightHolder | None = None,
    main_residence: bool = True,
) -> Dwelling:
    """:return: A decent main residence of 80 m² in zone 2, by default let by an agreed social landlord, not sublet."""
    return Dwelling(
        main_residence=main_residence,
        occupancy=social_tenancy() if occupancy is None else occupancy,
        owner=OtherRightHolder() if owner is None else owner,
        subletting=NotSublet(),
        usufructuary=OtherRightHolder() if usufructuary is None else usufructuary,
        decent=True,
        surface_square_metres=surface_square_metres,
        zone=HousingZone.ZONE_2,
    )


# %% persons


def dependent_child(
    birth_date: datetime.date,
    schooling_stage: SchoolingStage = SchoolingStage.DURING,
    nationality: Nationality | None = None,
    studying: bool = False,
) -> ChildDependant:
    """:return: A child earning nothing who already gave a right to family allowances, numbered by the birth date."""
    return ChildDependant(
        child=DependentChild(
            identifier=birth_date.toordinal(),
            nationality=French() if nationality is None else nationality,
            has_opened_family_allowance=True,
            birth_date=birth_date,
            monthly_pay=Money.zero,
            schooling_stage=schooling_stage,
            care_sharing=NoSharedResidence(),
            studying_or_unable_to_work=studying,
        )
    )


def applicant_born(
    birth_date: datetime.date = datetime.date(1970, 5, 2),
    nationality: Nationality | None = None,
    hosted_in_care_unit: bool = False,
    official_with_interests_outside_mayotte: bool = False,
) -> Applicant:
    """:return: An applicant born on *birth_date*, French unless said otherwise."""
    return Applicant(
        birth_date=birth_date,
        nationality=French() if nationality is None else nationality,
        hosted_in_care_unit=hosted_in_care_unit,
        non_salaried_farmer=False,
        official_with_interests_outside_mayotte=official_with_interests_outside_mayotte,
    )


# %% households


def housing_household(
    dependants: list[Dependant] | None = None,
    dwelling: Dwelling | None = None,
    family_situation: FamilySituation | None = None,
    residence: Territory = Territory.METROPOLITAN_FRANCE,
    other_occupants: int = 0,
    elderly_or_disabled: bool = False,
) -> HousingHousehold:
    """:return: A cohabiting couple in metropolitan France, receiving no family benefit, by default without persons in its charge."""
    return HousingHousehold(
        benefits_received=[],
        dwelling=dwelling_of() if dwelling is None else dwelling,
        dependants=[] if dependants is None else dependants,
        other_occupants=other_occupants,
        family_situation=Cohabiting() if family_situation is None else family_situation,
        attached_to_wealth_taxed_parent=False,
        child_expected_after_fourth_month=False,
        elderly_or_disabled_r844_4=elderly_or_disabled,
        residence=residence,
    )
