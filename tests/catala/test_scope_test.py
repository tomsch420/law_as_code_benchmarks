"""
Tests of mapping Catala structures onto domain dataclasses, and of tests about scopes.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from law_as_code_benchmarks.catala.exceptions import UnmodelledScope
from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.new_south_wales_community_gaming import (
    ClubBingoCase,
    DrawLotteryCase,
    OrganisationType,
)
from law_as_code_benchmarks.catala.reader import (
    CatalaLanguage,
    CatalaTestReader,
    ConstructorWithContent,
    Reference,
    StructureLiteral,
)
from law_as_code_benchmarks.catala.scope_test import ScopeTest
from law_as_code_benchmarks.catala.united_states_tax_code import (
    Period,
    PersonalData,
    SinglePersonCase,
)

# %% records


def test_a_structure_maps_onto_a_record_with_its_enumerations_converted() -> None:
    """
    A nested structure becomes its record, a constructor the enumeration's member, and
    each Catala name the field it maps onto.
    """
    case = DrawLotteryCase.from_catala(
        {
            "drawLottery": StructureLiteral(
                structure=Reference(parts=("DrawLottery",)),
                fields={
                    "typeOrg": Reference(parts=("NonProfit",)),
                    "grossProceeds": Money(cents=300000),
                    "totalValueOfThePrizes": Money(cents=400000),
                    "proceedsToBenefitingOrg": Money(cents=150000),
                },
            )
        }
    )
    assert (
        case.draw_lottery.organisation_type,
        case.draw_lottery.proceeds_to_benefiting_organisation,
    ) == (OrganisationType.NON_PROFIT, Money(cents=150000))


def test_a_list_of_structures_and_an_enumeration_with_content_map_onto_a_record() -> (
    None
):
    """
    Each structure of a list becomes its record, and the most recent sale § 121(a)
    applied to becomes its date.
    """
    period = StructureLiteral(
        structure=Reference(parts=("T", "Period")),
        fields={"begin": datetime.date(2017, 1, 1), "end": datetime.date(2021, 1, 1)},
    )
    data = PersonalData.from_catala(
        {
            "property_ownage": [period],
            "property_usage_as_principal_residence": [],
            "other_section_121a_sale": ConstructorWithContent(
                constructor=Reference(
                    parts=(
                        "T",
                        "OtherSection121aSale",
                        "MostRecentSaleWhereSection121aApplied",
                    )
                ),
                content=StructureLiteral(
                    structure=Reference(
                        parts=("T", "PreviousSaleWhereSection121aApplied")
                    ),
                    fields={"date_of_sale_or_exchange": datetime.date(2020, 3, 1)},
                ),
            ),
        }
    )
    assert data == PersonalData(
        property_ownage=[
            Period(begin=datetime.date(2017, 1, 1), end=datetime.date(2021, 1, 1))
        ],
        property_usage_as_principal_residence=[],
        previous_exclusion_sale_date=datetime.date(2020, 3, 1),
    )


# %% scope tests


def test_an_assertion_about_a_scope_no_case_models_is_refused() -> None:
    """
    A test asserting something of a scope the example's cases do not model is refused,
    not left out of the score.
    """
    path = Path(__file__).parent / "test_files" / "employee_discount.catala_en"
    program = CatalaTestReader(language=CatalaLanguage.ENGLISH).read_program(
        path.read_text()
    )
    with pytest.raises(UnmodelledScope):
        ScopeTest.from_scope(
            path.name,
            program.test_scopes[0],
            program,
            [ClubBingoCase, SinglePersonCase],
        )
