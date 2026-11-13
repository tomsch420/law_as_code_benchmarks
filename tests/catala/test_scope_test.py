"""
Tests of mapping Catala structures onto domain dataclasses, and of tests about scopes.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from pathlib import Path

import pytest
from krrood.ormatic.utils import classproperty

from law_as_code_benchmarks.catala.exceptions import (
    UnknownCatalaConstructor,
    UnmodelledScope,
)
from law_as_code_benchmarks.catala.housing.domain import (
    ChildCareSharing,
    Dependant,
    FamilySituation,
    Married,
    NoSharedResidence,
    SharedResidence,
    Single,
)
from law_as_code_benchmarks.catala.housing.eligibility import (
    EligibilityOutput,
    HousingAllowanceType,
)
from law_as_code_benchmarks.catala.housing.rented import RentedAidCase, RentedAidOutput
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
    CatalaValue,
    ConstructorWithContent,
    Reference,
    StructureLiteral,
)
from law_as_code_benchmarks.catala.scope_test import (
    OutputAssertion,
    ScopeCase,
    ScopeTest,
)
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


# %% enumerations whose constructors carry content


def test_a_constructor_with_content_maps_onto_its_subclass_holding_the_content() -> (
    None
):
    """
    A constructor given its content becomes an instance of the subclass standing for it,
    whatever module prefix leads to the constructor.
    """
    situation = FamilySituation.from_constructor(
        ConstructorWithContent(
            constructor=Reference(parts=("AL", "Mariés")),
            content=datetime.date(2010, 11, 26),
        )
    )
    assert isinstance(situation, Married)
    assert situation.wedding_date == datetime.date(2010, 11, 26)


def test_a_bare_constructor_maps_onto_its_subclass() -> None:
    """
    A constructor without content becomes an instance of its subclass.
    """
    assert isinstance(
        FamilySituation.from_constructor(Reference(parts=("Célibataire",))), Single
    )


def test_a_whole_number_content_becomes_a_fraction_where_one_is_asked() -> None:
    """
    A coefficient written as a whole number becomes the fraction the field holds.
    """
    sharing = ChildCareSharing.from_constructor(
        ConstructorWithContent(
            constructor=Reference(parts=("GardeAlternéeCoefficientPriseEnCharge",)),
            content=1,
        )
    )
    assert isinstance(sharing, SharedResidence)
    assert sharing.coefficient == Fraction(1)
    assert isinstance(
        ChildCareSharing.from_constructor(Reference(parts=("PasDeGardeAlternée",))),
        NoSharedResidence,
    )


def test_a_constructor_no_subclass_stands_for_is_refused() -> None:
    """
    A constructor of no known subclass is refused, not mapped onto the base class.
    """
    with pytest.raises(UnknownCatalaConstructor):
        Dependant.from_constructor(Reference(parts=("Inconnu",)))


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


def test_a_variable_defined_as_a_subscope_output_stands_for_that_output() -> None:
    """
    A test defining its own variable as a subscope's output and asserting the variable
    asserts the output itself.
    """
    program = read_french_program("output_alias.catala_fr")
    (scope,) = program.test_scopes
    test = ScopeTest.from_scope("output_alias.catala_fr", scope, program, [HiringCase])
    (assertion,) = test.assertions
    assert (assertion.variable, assertion.expected) == (
        HiringGrantOutput.ELIGIBILITY,
        True,
    )
    assert assertion.case.contract_kind == ContractKind.PERMANENT


@dataclass(eq=False)
class ConstantAllowanceCase(ScopeCase):
    """
    A case whose one output is always the family housing allowance.
    """

    @classproperty
    def catala_scope(cls) -> str:
        """
        A scope of no example.
        """
        return "Constante"

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """
        :class:`EligibilityOutput`.
        """
        return EligibilityOutput

    def output(self, variable: str) -> CatalaValue:
        return HousingAllowanceType.FAMILY


def test_a_variable_defined_as_an_output_applied_to_another_stands_for_the_application() -> (
    None
):
    """
    A test variable defined as a function output applied to another output asserts the
    function's value at that output.
    """
    program = read_french_program("applied_output.catala_fr")
    (scope,) = program.test_scopes
    test = ScopeTest.from_scope(
        "applied_output.catala_fr", scope, program, [RentedAidCase]
    )
    (assertion,) = test.assertions
    assert (assertion.variable, assertion.argument_output) == (
        RentedAidOutput.AID_TREATMENT,
        RentedAidOutput.INITIAL_AID,
    )
    case: RentedAidCase = assertion.case
    assert assertion.is_reproduced() == (
        case.treated_aid(case.output(RentedAidOutput.INITIAL_AID)) == assertion.expected
    )


def test_a_list_mapped_to_calls_gives_one_unasserted_case_per_element() -> None:
    """
    Each call a test maps a list to is a case of its own, which must conclude every
    output.
    """
    program = read_french_program("mapped_calls.catala_fr")
    (scope,) = program.test_scopes
    test = ScopeTest.from_scope("mapped_calls.catala_fr", scope, program, [HiringCase])
    assert sorted(case.assessment_date for case in test.unasserted_cases) == [
        datetime.date(2021, 11, 1),
        datetime.date(2022, 1, 1),
    ]


def test_an_enumeration_output_matches_a_qualified_constructor_of_its_name() -> None:
    """
    An output valued as an enumeration's member matches the constructor of that name
    whatever module prefix leads to it, and no other constructor.
    """
    case = ConstantAllowanceCase()
    family, social = (
        Reference(parts=("AL", "TypeÉligibilitéAllocationLogement", allowance.value))
        for allowance in (HousingAllowanceType.FAMILY, HousingAllowanceType.SOCIAL)
    )
    assert OutputAssertion(
        case=case, variable=EligibilityOutput.ELIGIBILITY, expected=family
    ).is_reproduced()
    assert not OutputAssertion(
        case=case, variable=EligibilityOutput.ELIGIBILITY, expected=social
    ).is_reproduced()


def test_a_call_of_a_scope_no_case_models_is_refused() -> None:
    """
    A test calling a scope the example's cases do not model is refused, even without
    assertions.
    """
    program = read_french_program("unmodelled_call.catala_fr")
    (scope,) = program.test_scopes
    with pytest.raises(UnmodelledScope):
        ScopeTest.from_scope("unmodelled_call.catala_fr", scope, program, [HiringCase])
