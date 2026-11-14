"""
Scores the models on the tests of Catala's examples: the share of test scopes whose
every assertion they reproduce, by example, and how long it takes.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
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
from law_as_code_benchmarks.stopwatch import Stopwatch

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
class ScopeResult:
    """
    How a model answered one test scope.
    """

    example: CatalaExample
    """
    The example the test belongs to.
    """

    identifier: str
    """
    The test's file and scope.
    """

    is_reproduced: bool
    """
    Whether the model concludes everything the test asserts.
    """

    seconds: float
    """
    How long the model took to answer, the test file read beforehand.
    """

    @classmethod
    def from_test(cls, example: CatalaExample, test: CatalaTest) -> ScopeResult:
        """:return: How the model of *example* answers *test*, timed."""
        stopwatch = Stopwatch()
        is_reproduced = test.is_reproduced()
        return cls(
            example=example,
            identifier=test.identifier,
            is_reproduced=is_reproduced,
            seconds=stopwatch.lap(),
        )


# %% every test


@dataclass
class CatalaScore:
    """
    The results of every test of the examples modelled.
    """

    results: list[ScopeResult] = field(default_factory=list)
    """
    One result per test, example by example.
    """

    @classmethod
    def from_examples(cls) -> CatalaScore:
        """:return: The results of the tests of every example."""
        return cls(
            results=[
                ScopeResult.from_test(example, test)
                for example in CatalaExample
                for test in example.read_tests()
            ]
        )

    def results_of(self, example: CatalaExample) -> list[ScopeResult]:
        """:return: The results of the tests of *example*."""
        return [result for result in self.results if result.example == example]

    def summary(self) -> str:
        """:return: The reproduced and total tests of each example and in all, and the times taken."""
        lines = [
            f"{example.value}: {self.reproduced_count(self.results_of(example))} of "
            f"{len(self.results_of(example))} tests reproduced"
            for example in CatalaExample
        ]
        lines.append(
            f"all examples: {self.reproduced_count(self.results)} of "
            f"{len(self.results)} tests reproduced"
        )
        milliseconds = [result.seconds * 1000 for result in self.results]
        lines.append(
            f"answering in krrood: median {statistics.median(milliseconds):.1f} ms, "
            f"maximum {max(milliseconds):.0f} ms"
        )
        return "\n".join(lines)

    @staticmethod
    def reproduced_count(results: list[ScopeResult]) -> int:
        """:return: How many of *results* are reproduced."""
        return sum(result.is_reproduced for result in results)
