"""
Scores the model on the tests of Catala's family benefits example: the share of test
scopes whose every assertion it reproduces, by test file, and how long it takes.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from law_as_code_benchmarks.catala.case import CatalaTestFile, FamilyBenefitsTest
from law_as_code_benchmarks.stopwatch import Stopwatch

# %% one test


@dataclass(frozen=True)
class ScopeResult:
    """
    How the model answered one test scope.
    """

    test_file: CatalaTestFile
    """
    The file holding the test.
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
    def from_test(cls, test: FamilyBenefitsTest) -> ScopeResult:
        """:return: How the model answers *test*, timed."""
        stopwatch = Stopwatch()
        is_reproduced = test.is_reproduced()
        return cls(
            test_file=test.test_file,
            identifier=test.identifier,
            is_reproduced=is_reproduced,
            seconds=stopwatch.lap(),
        )


# %% every test


@dataclass
class CatalaScore:
    """
    The results of every test of the example.
    """

    results: list[ScopeResult] = field(default_factory=list)
    """
    One result per test, file by file.
    """

    @classmethod
    def from_test_files(cls) -> CatalaScore:
        """:return: The results of the tests of every test file."""
        return cls(
            results=[
                ScopeResult.from_test(test)
                for test_file in CatalaTestFile
                for test in FamilyBenefitsTest.from_file(test_file)
            ]
        )

    def summary(self) -> str:
        """:return: The reproduced and total tests of each file and in all, and the times taken."""
        lines = []
        for test_file in CatalaTestFile:
            results = [
                result for result in self.results if result.test_file == test_file
            ]
            lines.append(
                f"{test_file.value}: {self.reproduced_count(results)} of "
                f"{len(results)} tests reproduced"
            )
        lines.append(
            f"all files: {self.reproduced_count(self.results)} of "
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
