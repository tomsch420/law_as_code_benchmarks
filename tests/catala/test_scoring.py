"""
Tests of scoring the model on the tests of Catala's family benefits example.
"""

from __future__ import annotations

from law_as_code_benchmarks.catala.scoring import CatalaScore

# %% the score


def test_every_test_of_the_example_is_reproduced() -> None:
    """
    The model reproduces every assertion of all 16 test scopes.
    """
    score = CatalaScore.from_test_files()
    assert [
        result.identifier for result in score.results if not result.is_reproduced
    ] == []
    assert CatalaScore.reproduced_count(score.results) == len(score.results) == 16
