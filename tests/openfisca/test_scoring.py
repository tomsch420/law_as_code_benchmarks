"""
Tests of scoring the family benefits model on OpenFisca France's tests.
"""

from __future__ import annotations

import pytest

from law_as_code_benchmarks.openfisca.scoring import (
    OpenFiscaResult,
    OpenFiscaScore,
    ReferenceOrigin,
)
from law_as_code_benchmarks.openfisca.yaml_test import OpenFiscaTestFile

# %% the summary


def test_the_summary_counts_by_origin_and_lists_the_misses() -> None:
    """
    Two tests of independent values, one reproduced, and one of OpenFisca's own.
    """
    score = OpenFiscaScore(
        results=[
            OpenFiscaResult(
                identifier="af.yaml:1",
                origin=ReferenceOrigin.INDEPENDENT,
                is_reproduced=True,
                seconds=0.002,
            ),
            OpenFiscaResult(
                identifier="af.yaml:2",
                origin=ReferenceOrigin.INDEPENDENT,
                is_reproduced=False,
                seconds=0.004,
            ),
            OpenFiscaResult(
                identifier="af_2020_04.yaml:1",
                origin=ReferenceOrigin.COMPUTED_BY_OPENFISCA,
                is_reproduced=True,
                seconds=0.003,
            ),
        ]
    )
    assert score.summary().splitlines() == [
        f"{ReferenceOrigin.INDEPENDENT.value}: 1 of 2 tests reproduced",
        f"{ReferenceOrigin.COMPUTED_BY_OPENFISCA.value}: 1 of 1 tests reproduced",
        "all tests: 2 of 3 tests reproduced",
        "not reproduced: af.yaml:2",
        "answering in krrood: median 3.0 ms, maximum 4 ms",
    ]


# %% OpenFisca France's own tests


@pytest.mark.skipif(
    not all(test_file.path.exists() for test_file in OpenFiscaTestFile),
    reason="OpenFisca France's tests are not fetched: run scripts/fetch_openfisca_tests.py",
)
def test_the_model_reproduces_80_of_openfiscas_93_tests() -> None:
    """
    76 of the 88 tests of independent values and 4 of the 5 of OpenFisca's own.
    """
    score = OpenFiscaScore.from_test_files()
    assert [
        (
            score.reproduced_count(score.results_of(origin)),
            len(score.results_of(origin)),
        )
        for origin in ReferenceOrigin
    ] == [(76, 88), (4, 5)]
