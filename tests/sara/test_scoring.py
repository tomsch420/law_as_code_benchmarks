"""
Tests of scoring a split of SARA's cases.
"""

from __future__ import annotations

from law_as_code_benchmarks.sara.case import SaraCase, SaraSplit
from law_as_code_benchmarks.sara.provision import SaraPredicate
from law_as_code_benchmarks.sara.scoring import (
    AmountPredicate,
    AnswerKind,
    CaseResult,
    SplitScore,
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
    result = CaseResult.from_case(SaraCase.load("tax_case_8", swipl))
    assert (result.kind, result.is_modelled, result.is_correct) == (
        AnswerKind.AMOUNT,
        False,
        False,
    )


# %% the test split


def test_the_test_split_models_two_cases_per_provision(swipl: str) -> None:
    """
    Scoring the test split models exactly the cases of the modelled provisions.
    """
    score = SplitScore.from_split(SaraSplit.TEST, swipl)
    modelled = [result for result in score.results if result.is_modelled]
    assert len(score.results) == len(SaraSplit.TEST.case_identifiers())
    assert len(modelled) == 2 * len(SaraPredicate)
    assert all(result.kind == AnswerKind.ENTAILMENT for result in modelled)
