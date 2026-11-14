"""
Tests of scoring a model on a benchmark's tests.
"""

from __future__ import annotations

from dataclasses import dataclass

from law_as_code_benchmarks.law.scoring import (
    ReproducibleTest,
    ReproductionResult,
    Score,
)

# %% a test whose answer is fixed


@dataclass
class FixedAnswerTest(ReproducibleTest):
    """
    A test the model reproduces or not, as stated.
    """

    name: str
    """The test's name."""

    reproduced: bool
    """
    Whether the model reproduces it.
    """

    @property
    def identifier(self) -> str:
        return self.name

    def is_reproduced(self) -> bool:
        return self.reproduced


# %% one test


def test_a_result_records_the_test_and_whether_it_is_reproduced() -> None:
    """
    The result names the test and how the model answered.
    """
    result = ReproductionResult.from_test(FixedAnswerTest(name="a", reproduced=True))
    assert (result.identifier, result.is_reproduced) == ("a", True)
    assert result.seconds >= 0


# %% every test


def score() -> Score[ReproductionResult]:
    """:return: Two results, one reproduced, taking 2 and 4 ms."""
    return Score(
        results=[
            ReproductionResult(identifier="a", is_reproduced=True, seconds=0.002),
            ReproductionResult(identifier="b", is_reproduced=False, seconds=0.004),
        ]
    )


def test_the_reproduced_line_counts_the_reproduced_results() -> None:
    """
    One of two tests is reproduced.
    """
    assert (
        Score.reproduced_line("all tests", score().results)
        == "all tests: 1 of 2 tests reproduced"
    )


def test_the_answering_time_line_gives_the_median_and_maximum() -> None:
    """
    The median of 2 and 4 ms is 3 ms.
    """
    assert (
        score().answering_time_line()
        == "answering in krrood: median 3.0 ms, maximum 4 ms"
    )
