"""
Scores the family benefits model on OpenFisca France's family allowance tests: the share
of tests whose every output it computes within the test's error margin, apart for the
tests whose values OpenFisca computed itself.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from enum import StrEnum

from law_as_code_benchmarks.openfisca.yaml_test import OpenFiscaTest, OpenFiscaTestFile
from law_as_code_benchmarks.stopwatch import Stopwatch

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
class OpenFiscaResult:
    """
    How the model answered one test.
    """

    identifier: str
    """
    The test's file and number.
    """

    origin: ReferenceOrigin
    """
    Where the values the test expects come from.
    """

    is_reproduced: bool
    """
    Whether every output computed is within the test's margin.
    """

    seconds: float
    """
    How long the model took to answer, the test file read beforehand.
    """

    @classmethod
    def from_test(cls, test: OpenFiscaTest) -> OpenFiscaResult:
        """:return: How the model answers *test*, timed."""
        stopwatch = Stopwatch()
        is_reproduced = test.is_reproduced()
        return cls(
            identifier=test.identifier,
            origin=ReferenceOrigin.from_test(test),
            is_reproduced=is_reproduced,
            seconds=stopwatch.lap(),
        )


# %% every test


@dataclass
class OpenFiscaScore:
    """
    The results of every family allowance test of OpenFisca France.
    """

    results: list[OpenFiscaResult] = field(default_factory=list)
    """
    One result per test, file by file.
    """

    @classmethod
    def from_test_files(cls) -> OpenFiscaScore:
        """:return: The results of the tests of every file, fetched beforehand."""
        return cls(
            results=[
                OpenFiscaResult.from_test(test)
                for test_file in OpenFiscaTestFile
                for test in test_file.read_tests()
            ]
        )

    def results_of(self, origin: ReferenceOrigin) -> list[OpenFiscaResult]:
        """:return: The results of the tests whose values come from *origin*."""
        return [result for result in self.results if result.origin == origin]

    def summary(self) -> str:
        """:return: The reproduced and total tests by origin and in all, the misses, and the times taken."""
        lines = [
            f"{origin.value}: {self.reproduced_count(self.results_of(origin))} of "
            f"{len(self.results_of(origin))} tests reproduced"
            for origin in ReferenceOrigin
        ]
        lines.append(
            f"all tests: {self.reproduced_count(self.results)} of "
            f"{len(self.results)} tests reproduced"
        )
        lines.extend(
            f"not reproduced: {result.identifier}"
            for result in self.results
            if not result.is_reproduced
        )
        milliseconds = [result.seconds * 1000 for result in self.results]
        lines.append(
            f"answering in krrood: median {statistics.median(milliseconds):.1f} ms, "
            f"maximum {max(milliseconds):.0f} ms"
        )
        return "\n".join(lines)

    @staticmethod
    def reproduced_count(results: list[OpenFiscaResult]) -> int:
        """:return: How many of *results* are reproduced."""
        return sum(result.is_reproduced for result in results)
