"""
Tests of the models of Catala's ASP examples, on cases the examples' own tests leave
out.
"""

from __future__ import annotations

import dataclasses
import datetime
from fractions import Fraction

import pytest
from typing_extensions import Any

from law_as_code_benchmarks.catala.crop_rotation import (
    Crop,
    CropCode,
    CropQualification,
    CropRotationOutput,
    CropRotationTestFile,
    FarmCase,
    MultiYearCriterionProvision,
    Parcel,
    ParcelSystem,
)
from law_as_code_benchmarks.law.period import Period
from law_as_code_benchmarks.catala.exceptions import UncategorisedCrop
from law_as_code_benchmarks.catala.fibre_connection_grant import (
    AnnexCommunes,
    Business,
    FibreConnectionCase,
    FibreGrantOutput,
    FibreGrantTestFile,
)
from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.performing_arts_hiring_grant import (
    BusinessRegime,
    ContractKind,
    Grant,
    HiringCase,
    HiringGrantOutput,
    HiringGrantTestFile,
    PaymentFrequency,
)
from law_as_code_benchmarks.catala.reader import (
    CatalaLanguage,
    CatalaTestReader,
    Reference,
)
from law_as_code_benchmarks.catala.scope_test import ScopeTest

# %% the hiring grant


@pytest.fixture
def full_time_permanent_hiring() -> HiringCase:
    """
    The hiring of the example's test, on a full-time permanent contract instead.
    """
    (test,) = HiringGrantTestFile.HIRING_GRANT.read_tests()
    (case,) = test.unasserted_cases
    return dataclasses.replace(
        case,
        contract_kind=ContractKind.PERMANENT,
        fixed_term_months=None,
        part_time_share=None,
        drawn_conclusions={},
    )


def test_a_full_time_permanent_contract_earns_10_000_euros_a_year_for_three_years(
    full_time_permanent_hiring: HiringCase,
) -> None:
    """
    Article 3: 10,000 € a year for three years.
    """
    assert full_time_permanent_hiring.output(HiringGrantOutput.AMOUNT) == Grant(
        amount=Money.from_euros(10_000),
        frequency=PaymentFrequency.ANNUAL,
        instalment_count=3,
    )


def test_replacing_a_choir_singer_who_changed_duties_raises_the_grant_to_16_000_euros(
    full_time_permanent_hiring: HiringCase,
) -> None:
    """
    Article 3: a permanent choir singer hired to replace one who changed duties with the
    same employer earns 16,000 € a year, even part time before prorating.
    """
    case = dataclasses.replace(
        full_time_permanent_hiring,
        business_regime=BusinessRegime.LISTED_LYRIC_ARTISTS_EMPLOYER,
        permanent_choir_singer=True,
        replaces_singer_who_changed_duties=True,
        part_time_share=Fraction(1, 2),
    )
    assert case.output(HiringGrantOutput.AMOUNT) == Grant(
        amount=Money.from_euros(8_000),
        frequency=PaymentFrequency.ANNUAL,
        instalment_count=3,
    )
    assert case.output(HiringGrantOutput.ELIGIBILITY)


@pytest.mark.parametrize(
    "changes",
    [
        {
            "contract_kind": ContractKind.FIXED_TERM,
            "fixed_term_months": 1,
        },
        {
            "contract_kind": ContractKind.FIXED_TERM,
            "fixed_term_months": 6,
            "school_resident_voice_artist": True,
            "business_regime": BusinessRegime.LISTED_LYRIC_ARTISTS_EMPLOYER,
        },
        {"annual_gross_salary": Money.from_euros(80_000)},
        {"contract_start_date": datetime.date(2023, 1, 1)},
        {"performing_arts_duties": False},
    ],
)
def test_a_hiring_failing_a_requirement_is_not_eligible(
    full_time_permanent_hiring: HiringCase, changes: dict[str, Any]
) -> None:
    """
    Articles 1 and 2: a fixed term of a month only, a resident voice artist's contract
    of six months, a salary above four annual minimum wages (74,619.96 € in 2021), a
    contract begun after 2022, or duties outside the performing arts.
    """
    case = dataclasses.replace(full_time_permanent_hiring, **changes)
    assert not case.output(HiringGrantOutput.ELIGIBILITY)


def test_a_full_time_resident_voice_artist_earns_a_single_9_000_euros(
    full_time_permanent_hiring: HiringCase,
) -> None:
    """
    Article 3: a full-time fixed term of a voice artist in residence in a school earns
    9,000 € once.
    """
    case = dataclasses.replace(
        full_time_permanent_hiring,
        contract_kind=ContractKind.FIXED_TERM,
        fixed_term_months=7,
        school_resident_voice_artist=True,
    )
    assert case.output(HiringGrantOutput.AMOUNT) == Grant(
        amount=Money.from_euros(9_000),
        frequency=PaymentFrequency.SINGLE,
        instalment_count=1,
    )


# %% the fibre connection grant


@pytest.fixture
def individual_application() -> FibreConnectionCase:
    """
    The application of the example's test, by a natural person in Martinique.
    """
    (test,) = FibreGrantTestFile.FIBRE_GRANT.read_tests()
    return test.assertions[0].case


@pytest.fixture
def business_application(
    individual_application: FibreConnectionCase,
) -> FibreConnectionCase:
    """
    The same works, applied for by a small business of the same commune.
    """
    return dataclasses.replace(
        individual_application,
        individual=None,
        business=Business(
            turnover=Money.from_euros(500_000),
            employee_count=4,
            activity_start=datetime.date(2020, 3, 1),
            in_judicial_liquidation=False,
            postal_code=individual_application.individual.postal_code,
            not_previously_aided=True,
            connection_failure_recorded=True,
        ),
        drawn_conclusions={},
    )


def test_a_small_business_is_eligible(
    business_application: FibreConnectionCase,
) -> None:
    """
    Article 3 II: a business meeting 1° to 7° is eligible.
    """
    assert business_application.output(FibreGrantOutput.ELIGIBILITY)


@pytest.mark.parametrize(
    "changes",
    [
        {"activity_start": datetime.date(2025, 3, 1)},
        {"employee_count": 11},
        {"in_judicial_liquidation": True},
        {"postal_code": 75001},
    ],
)
def test_a_business_failing_a_requirement_is_not_eligible(
    business_application: FibreConnectionCase, changes: dict[str, Any]
) -> None:
    """
    Article 3 II: a business active for less than a year on the application date, with
    more than 10 employees, in judicial liquidation, or in a commune the annex leaves
    out.
    """
    case = dataclasses.replace(
        business_application,
        business=dataclasses.replace(business_application.business, **changes),
    )
    assert not case.output(FibreGrantOutput.ELIGIBILITY)


def test_works_completed_before_september_2025_are_not_eligible(
    individual_application: FibreConnectionCase,
) -> None:
    """
    Article 1: the works are completed from 1 September 2025 on.
    """
    case = dataclasses.replace(
        individual_application,
        completion_date=datetime.date(2025, 8, 31),
        drawn_conclusions={},
    )
    assert not case.output(FibreGrantOutput.ELIGIBILITY)


def test_the_invoice_caps_the_grant(
    individual_application: FibreConnectionCase,
) -> None:
    """
    Article 4: the grant is at most the invoice's amount.
    """
    invoice = Money.from_euros(700)
    case = dataclasses.replace(
        individual_application, invoice_amount=invoice, drawn_conclusions={}
    )
    assert case.output(FibreGrantOutput.AMOUNT) == invoice


def test_the_annex_lists_the_communes_of_the_example() -> None:
    """
    The postal codes are those of the example's OCaml module, Martinique's 97233 among
    them.
    """
    assert 97233 in AnnexCommunes.from_example().postal_codes
    assert 75001 not in AnnexCommunes.from_example().postal_codes


# %% the crop rotation standard


@pytest.fixture
def fifth_example() -> FarmCase:
    """
    The farm of the technical sheet's fifth example, with its parcel in maize
    monoculture.
    """
    (*_, test) = CropRotationTestFile.CROP_ROTATION.read_tests()
    return test.assertions[0].case


def test_the_fifth_example_without_its_maize_monoculture_is_respected() -> None:
    """
    ``Exemple5bis``, which carries no ``#[test]``: without the parcel in maize
    monoculture, every parcel meets the multi-year criterion.
    """
    test_file = CropRotationTestFile.CROP_ROTATION
    program = CatalaTestReader(language=CatalaLanguage.FRENCH).read_program(
        test_file.path.read_text()
    )
    (scope,) = [scope for scope in program.scopes if scope.name == "Exemple5bis"]
    test = ScopeTest.from_scope(test_file.value, scope, program, test_file.scope_cases)
    assert test.is_reproduced()


def test_the_maize_monoculture_misses_the_multi_year_criterion_by_its_area(
    fifth_example: FarmCase,
) -> None:
    """
    The parcel in maize monoculture misses the multi-year criterion: the shortfall is
    its 15 hectares, a fifth of the farm's 75 cultivated hectares.
    """
    criterion = fifth_example.sole_conclusion(MultiYearCriterionProvision)
    assert (criterion.shortfall_hectares, criterion.shortfall_proportion) == (
        Fraction(15),
        Fraction(1, 5),
    )


def test_seed_maize_meets_the_multi_year_criterion_by_exception(
    fifth_example: FarmCase,
) -> None:
    """
    The exemption for seed maize: the monoculture of seed maize meets the multi-year
    criterion.
    """
    parcels = [
        dataclasses.replace(
            parcel,
            crops=[
                dataclasses.replace(crop, code=CropCode.MIS)
                if crop.code == CropCode.MID
                else crop
                for crop in parcel.crops
            ],
        )
        for parcel in fifth_example.parcels
    ]
    case = dataclasses.replace(fifth_example, parcels=parcels, drawn_conclusions={})
    assert case.output(CropRotationOutput.MULTI_YEAR_CRITERION) == Reference(
        parts=("Respecté",)
    )


def test_a_spring_monoculture_without_winter_cover_misses_the_multi_year_criterion(
    fifth_example: FarmCase,
) -> None:
    """
    A parcel of wheat then sunflower meets the multi-year criterion; in spring
    monoculture it also needs a secondary crop on 15 November of each year, still grown
    on 15 February, which it lacks.
    """
    (rotating, *_) = fifth_example.parcels
    rotating_case = dataclasses.replace(
        fifth_example, parcels=[rotating], drawn_conclusions={}
    )
    monoculture = dataclasses.replace(rotating, system=ParcelSystem.SPRING_MONOCULTURE)
    monoculture_case = dataclasses.replace(
        fifth_example, parcels=[monoculture], drawn_conclusions={}
    )
    assert rotating_case.output(CropRotationOutput.MULTI_YEAR_CRITERION) == Reference(
        parts=("Respecté",)
    )
    criterion = monoculture_case.sole_conclusion(MultiYearCriterionProvision)
    assert criterion.shortfall_hectares == monoculture.area_hectares


def test_a_crop_in_no_category_cannot_be_compared() -> None:
    """
    Annex 4 puts carrots (*CAR*) in no category, which Catala's example declares
    impossible.
    """
    with pytest.raises(UncategorisedCrop):
        CropCode.CAR.category


def test_the_crop_on_a_day_is_grown_on_both_ends_of_its_period() -> None:
    """
    A crop is grown on the first and last day of its period, and on no day after.
    """
    crop = Crop(
        code=CropCode.PTR,
        period=Period(datetime.date(2023, 1, 1), datetime.date(2025, 12, 31)),
        qualification=CropQualification.PRINCIPAL,
    )
    parcel = Parcel(area_hectares=Fraction(1), crops=[crop], system=ParcelSystem.OTHER)
    assert parcel.crop_on(datetime.date(2023, 1, 1)) == crop
    assert parcel.crop_on(datetime.date(2025, 12, 31)) == crop
    assert parcel.crop_on(datetime.date(2026, 1, 1)) is None
