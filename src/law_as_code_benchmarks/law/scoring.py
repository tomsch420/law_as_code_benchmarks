"""
Scores of a model on a benchmark's tests: whether it reproduces each test's reference
answers, and how long it takes.
"""

from __future__ import annotations

import statistics
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from krrood.patterns.subclass_safe_generic import SubClassSafeGeneric
from typing_extensions import Any, Generic, Self, TypeVar

from law_as_code_benchmarks.stopwatch import Stopwatch

# %% tests


class ReproducibleTest(ABC):
    """
    A test of a benchmark, and whether a model reproduces its reference answers.
    """

    @property
    @abstractmethod
    def identifier(self) -> str:
        """
        What names the test uniquely among the benchmark's tests.
        """

    @abstractmethod
    def is_reproduced(self) -> bool:
        """:return: Whether the model gives every answer the test expects."""


# %% one test


@dataclass(frozen=True)
class ReproductionResult:
    """
    How a model answered one test.
    """

    identifier: str
    """
    The identifier of the test.
    """

    is_reproduced: bool
    """
    Whether the model gives every answer the test expects.
    """

    seconds: float
    """
    How long the model took to answer, the test read beforehand.
    """

    @classmethod
    def from_test(cls, test: ReproducibleTest, **fields: Any) -> Self:
        """
        :param test: The test answered, timed.
        :param fields: The values of the fields a subclass adds.
        :return: How the model answers *test*.
        """
        stopwatch = Stopwatch()
        is_reproduced = test.is_reproduced()
        return cls(
            identifier=test.identifier,
            is_reproduced=is_reproduced,
            seconds=stopwatch.lap(),
            **fields,
        )


ResultType = TypeVar("ResultType", bound=ReproductionResult)


# %% every test


@dataclass
class Score(Generic[ResultType], SubClassSafeGeneric):
    """
    The results of a model on a benchmark's tests.
    """

    results: list[ResultType] = field(default_factory=list)
    """
    One result per test, in the benchmark's order.
    """

    @staticmethod
    def reproduced_count(results: list[ResultType]) -> int:
        """:return: How many of *results* are reproduced."""
        return sum(result.is_reproduced for result in results)

    @classmethod
    def reproduced_line(cls, label: str, results: list[ResultType]) -> str:
        """:return: The line reporting how many of *results*, which *label* names, are reproduced."""
        return f"{label}: {cls.reproduced_count(results)} of {len(results)} tests reproduced"

    def answering_time_line(self) -> str:
        """:return: The line reporting the median and maximum time the model took to answer a test."""
        milliseconds = [result.seconds * 1000 for result in self.results]
        return (
            f"answering in krrood: median {statistics.median(milliseconds):.1f} ms, "
            f"maximum {max(milliseconds):.0f} ms"
        )
