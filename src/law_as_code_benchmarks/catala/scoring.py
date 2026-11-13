"""
Scores the models on the tests of Catala's examples: the share of test scopes whose
every assertion they reproduce, by example, and how long it takes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from law_as_code_benchmarks.catala.case import CatalaTestFile, FamilyBenefitsTest
from law_as_code_benchmarks.catala.crop_rotation import CropRotationTestFile
from law_as_code_benchmarks.catala.fibre_connection_grant import FibreGrantTestFile
from law_as_code_benchmarks.catala.housing.calculator import CalculatorTestFile
from law_as_code_benchmarks.catala.housing.eligibility import EligibilityTestFile
from law_as_code_benchmarks.catala.housing.ownership import OwnershipTestFile
from law_as_code_benchmarks.catala.housing.rented import RentedTestFile
from law_as_code_benchmarks.catala.housing.residence_hall import (
    ResidenceHallTestFile,
)
from law_as_code_benchmarks.catala.income_tax.test_files import IncomeTaxTestFile
from law_as_code_benchmarks.catala.inheritance import InheritanceTestFile
from law_as_code_benchmarks.catala.new_south_wales_community_gaming import (
    NewSouthWalesCommunityGamingTestFile,
)
from law_as_code_benchmarks.catala.performing_arts_hiring_grant import (
    HiringGrantTestFile,
)
from law_as_code_benchmarks.catala.polish_tax import PolishTaxTestFile
from law_as_code_benchmarks.catala.scope_test import CatalaTest
from law_as_code_benchmarks.catala.united_states_tax_code import (
    UnitedStatesTaxCodeTestFile,
)
from law_as_code_benchmarks.law.scoring import ReproductionResult, Score

# %% examples


class CatalaExample(StrEnum):
    """
    The examples of catala-examples modelled, each named after its directory.
    """

    FAMILY_BENEFITS = "allocations_familiales"
    """
    French family benefits, with ``prestations_familiales``.
    """

    INHERITANCE = "droit_successions"
    """
    The reserved portion of an estate under the French Code civil.
    """

    POLISH_TAXES = "polish_taxes"
    """
    The rates of the Polish tax on civil-law transactions.
    """

    UNITED_STATES_TAX_CODE = "us_tax_code"
    """
    Sections 121 and 132 of the United States Internal Revenue Code.
    """

    NEW_SOUTH_WALES_COMMUNITY_GAMING = "NSW_community_gaming"
    """
    The permitted gaming activities of New South Wales.
    """

    CROP_ROTATION = "asp/bcae7"
    """
    The crop rotation standard of the 2025 conditionality of the common agricultural
    policy.
    """

    FIBRE_CONNECTION_GRANT = "asp/aide_fibre"
    """
    The grant for private works connecting a building to optical fibre.
    """

    PERFORMING_ARTS_HIRING_GRANT = "asp/fonpeps"
    """
    The hiring grant of the national fund for permanent employment in the performing
    arts.
    """

    HOUSING_AIDS = "aides_logement"
    """
    The French personal housing aids.
    """

    INCOME_TAX = "impot_revenu"
    """
    The French income tax, its tests fetched rather than kept in the repository.
    """

    def read_tests(self) -> list[CatalaTest]:
        """:return: The tests of every test file of the example, in order."""
        match self:
            case CatalaExample.FAMILY_BENEFITS:
                return [
                    test
                    for test_file in CatalaTestFile
                    for test in FamilyBenefitsTest.from_file(test_file)
                ]
            case CatalaExample.INHERITANCE:
                test_files = list(InheritanceTestFile)
            case CatalaExample.POLISH_TAXES:
                test_files = list(PolishTaxTestFile)
            case CatalaExample.UNITED_STATES_TAX_CODE:
                test_files = list(UnitedStatesTaxCodeTestFile)
            case CatalaExample.NEW_SOUTH_WALES_COMMUNITY_GAMING:
                test_files = list(NewSouthWalesCommunityGamingTestFile)
            case CatalaExample.CROP_ROTATION:
                test_files = list(CropRotationTestFile)
            case CatalaExample.FIBRE_CONNECTION_GRANT:
                test_files = list(FibreGrantTestFile)
            case CatalaExample.PERFORMING_ARTS_HIRING_GRANT:
                test_files = list(HiringGrantTestFile)
            case CatalaExample.INCOME_TAX:
                test_files = list(IncomeTaxTestFile)
            case CatalaExample.HOUSING_AIDS:
                test_files = [
                    *EligibilityTestFile,
                    *RentedTestFile,
                    *OwnershipTestFile,
                    *ResidenceHallTestFile,
                    *CalculatorTestFile,
                ]
        return [test for test_file in test_files for test in test_file.read_tests()]


# %% one test


@dataclass(frozen=True)
class ScopeResult(ReproductionResult):
    """
    How a model answered one test scope.
    """

    example: CatalaExample
    """
    The example the test belongs to.
    """


# %% every test


@dataclass
class CatalaScore(Score[ScopeResult]):
    """
    The results of every test of the examples modelled, example by example.
    """

    @classmethod
    def from_examples(cls, examples: list[CatalaExample] | None = None) -> CatalaScore:
        """:return: The results of the tests of *examples*, every example where none are given."""
        return cls(
            results=[
                ScopeResult.from_test(test, example=example)
                for example in (list(CatalaExample) if examples is None else examples)
                for test in example.read_tests()
            ]
        )

    def results_of(self, example: CatalaExample) -> list[ScopeResult]:
        """:return: The results of the tests of *example*."""
        return [result for result in self.results if result.example == example]

    def summary(self) -> str:
        """:return: The reproduced and total tests of each example and in all, and the times taken."""
        return "\n".join(
            [
                *(
                    self.reproduced_line(example.value, self.results_of(example))
                    for example in CatalaExample
                ),
                self.reproduced_line("all examples", self.results),
                self.answering_time_line(),
            ]
        )
