"""
Scores the family benefits model on OpenFisca France's family allowance tests: the share
of tests whose every output it computes within the test's error margin, apart for the
tests whose values OpenFisca computed itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from law_as_code_benchmarks.openfisca.yaml_test import OpenFiscaTest, OpenFiscaTestFile
from law_as_code_benchmarks.law.scoring import ReproductionResult, Score

# %% where the expected values come from


class ReferenceOrigin(StrEnum):
    """
    Where the values a test expects come from, each worded as the summary prints it.
    """

    INDEPENDENT = "values from published amounts or outside cases"
    """
    Published amounts and rates, or cases stated outside OpenFisca.
    """

    COMPUTED_BY_OPENFISCA = "values OpenFisca computed itself"
    """
    OpenFisca's own results.
    """

    @classmethod
    def from_test(cls, test: OpenFiscaTest) -> ReferenceOrigin:
        """:return: Where the values *test* expects come from."""
        return (
            cls.COMPUTED_BY_OPENFISCA
            if test.is_computed_by_openfisca
            else cls.INDEPENDENT
        )


# %% one test


@dataclass(frozen=True)
class OpenFiscaResult(ReproductionResult):
    """
    How the model answered one test.
    """

    origin: ReferenceOrigin
    """
    Where the values the test expects come from.
    """


# %% every test


@dataclass
class OpenFiscaScore(Score[OpenFiscaResult]):
    """
    The results of every family allowance test of OpenFisca France, file by file.
    """

    @classmethod
    def from_test_files(cls) -> OpenFiscaScore:
        """:return: The results of the tests of every file, fetched beforehand."""
        return cls(
            results=[
                OpenFiscaResult.from_test(test, origin=ReferenceOrigin.from_test(test))
                for test_file in OpenFiscaTestFile
                for test in test_file.read_tests()
            ]
        )

    def results_of(self, origin: ReferenceOrigin) -> list[OpenFiscaResult]:
        """:return: The results of the tests whose values come from *origin*."""
        return [result for result in self.results if result.origin == origin]

    def summary(self) -> str:
        """:return: The reproduced and total tests by origin and in all, the misses, and the times taken."""
        return "\n".join(
            [
                *(
                    self.reproduced_line(origin.value, self.results_of(origin))
                    for origin in ReferenceOrigin
                ),
                self.reproduced_line("all tests", self.results),
                *(
                    f"not reproduced: {result.identifier}"
                    for result in self.results
                    if not result.is_reproduced
                ),
                self.answering_time_line(),
            ]
        )
