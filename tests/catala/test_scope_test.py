"""
Tests of mapping Catala structures onto domain dataclasses, and of tests about scopes.
"""

from __future__ import annotations

import datetime
from fractions import Fraction
from pathlib import Path

import pytest

from law_as_code_benchmarks.catala.exceptions import UnmodelledScope
from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.new_south_wales_community_gaming import (
    ClubBingoCase,
    DrawLotteryCase,
    OrganisationType,
)
from law_as_code_benchmarks.catala.performing_arts_hiring_grant import (
    ContractKind,
    HiringCase,
    HiringGrantOutput,
)
from law_as_code_benchmarks.catala.reader import (
    CatalaLanguage,
    CatalaProgram,
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


def read_french_program(file_name: str) -> CatalaProgram:
    """:return: The program of :file:`test_files/{file_name}`, read in French."""
    path = Path(__file__).parent / "test_files" / file_name
    return CatalaTestReader(language=CatalaLanguage.FRENCH).read_program(
        path.read_text()
    )


def test_a_scope_called_without_assertions_needs_every_output_concluded() -> None:
    """
    A test calling a scope and asserting nothing of it builds the call's case from its
    arguments; it is not reproduced where an output has no value, as Catala's test fails
    when no rule defines one.
    """
    program = read_french_program("unasserted_call.catala_fr")
    (scope,) = program.test_scopes
    test = ScopeTest.from_scope(
        "unasserted_call.catala_fr", scope, program, [HiringCase]
    )
    (case,) = test.unasserted_cases
    assert (case.contract_kind, case.part_time_share, case.fixed_term_months) == (
        ContractKind.PERMANENT,
        Fraction(1, 2),
        None,
    )
    assert case.output(HiringGrantOutput.AMOUNT) is None
    assert not test.is_reproduced()


def test_a_call_of_a_scope_no_case_models_is_refused() -> None:
    """
    A test calling a scope the example's cases do not model is refused, even without
    assertions.
    """
    program = read_french_program("unmodelled_call.catala_fr")
    (scope,) = program.test_scopes
    with pytest.raises(UnmodelledScope):
        ScopeTest.from_scope("unmodelled_call.catala_fr", scope, program, [HiringCase])
