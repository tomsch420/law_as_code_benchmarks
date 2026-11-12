"""
Tests of scoring a split of SARA's cases.
"""

from __future__ import annotations

import statistics

from law_as_code_benchmarks.sara.case import SaraSplit
from law_as_code_benchmarks.sara.scoring import (
    AmountPredicate,
    AnswerKind,
    CaseResult,
    SplitScore,
    TimedStage,
)

# %% one case


def test_a_tax_case_asks_for_an_amount() -> None:
    """
    A goal of the predicate ``tax`` asks for an amount.
    """
    assert AnswerKind.from_predicate(AmountPredicate.TAX) == AnswerKind.AMOUNT


def test_a_case_about_an_unmodelled_provision_is_not_modelled(swipl: str) -> None:
    """
    A case asking about an unmodelled provision counts as unmodelled and not correct.
    """
    result = CaseResult.from_identifier("s3306_a_1_pos", swipl)
    assert (result.kind, result.is_modelled, result.is_correct) == (
        AnswerKind.ENTAILMENT,
        False,
        False,
    )


# %% the test split


def test_the_test_split_models_every_case(swipl: str) -> None:
    """
    Scoring the test split models each of its cases, entailment and amount alike.
    """
    score = SplitScore.from_split(SaraSplit.TEST, swipl)
    assert [result.identifier for result in score.results if result.is_modelled] == (
        SaraSplit.TEST.case_identifiers()
    )


# %% timing


def test_a_modelled_case_times_every_stage(swipl: str) -> None:
    """
    A modelled case records a non-negative duration for every stage, SARA's program
    included.
    """
    result = CaseResult.from_identifier("s3306_c_6_pos", swipl)
    assert set(result.durations) == set(TimedStage)
    assert all(seconds >= 0 for seconds in result.durations.values())
    assert result.reference_passed


def test_an_unmodelled_case_is_not_timed(swipl: str) -> None:
    """
    A case about an unmodelled provision is not answered, so no stage is timed.
    """
    assert CaseResult.from_identifier("s3306_a_1_pos", swipl).durations == {}


def timed_result(identifier: str, seconds: float) -> CaseResult:
    """:return: A correct entailment result whose every stage took *seconds*."""
    return CaseResult(
        identifier=identifier,
        kind=AnswerKind.ENTAILMENT,
        is_modelled=True,
        is_correct=True,
        durations={stage: seconds for stage in TimedStage},
        reference_passed=True,
    )


def test_the_timing_summary_reports_median_maximum_and_total_per_stage() -> None:
    """
    The timing summary gives, per stage, the median, the maximum and the total over the
    modelled cases.
    """
    durations = [0.001, 0.002, 0.009]
    score = SplitScore(
        split=SaraSplit.TEST,
        results=[
            timed_result(f"case_{index}", seconds)
            for index, seconds in enumerate(durations)
        ],
    )
    stage_lines = score.timing_summary()[2:]
    assert stage_lines == [
        f"  {stage.value}: {statistics.median(durations) * 1000:.3f} ms median, "
        f"{max(durations) * 1000:.3f} ms maximum, {sum(durations) * 1000:.1f} ms total"
        for stage in TimedStage
    ]
