"""
Tests of scoring the models on the tests of the Catala examples.
"""

from __future__ import annotations

import pytest

from law_as_code_benchmarks.catala.income_tax.test_files import IncomeTaxTestFile
from law_as_code_benchmarks.catala.scoring import CatalaExample, CatalaScore

# %% the score


def test_every_test_of_every_example_kept_here_is_reproduced() -> None:
    """
    The models reproduce every assertion of all 102 test scopes kept in the repository:
    16 of the family benefits, 4 of inheritance, 8 of the Polish tax, 9 of the US tax
    code, 25 of New South Wales' gaming, 5 of crop rotation, 1 of the fibre grant, 1 of
    the hiring grant and 33 of the housing aids.
    """
    kept = [example for example in CatalaExample if example != CatalaExample.INCOME_TAX]
    score = CatalaScore.from_examples(kept)
    assert [
        result.identifier for result in score.results if not result.is_reproduced
    ] == []
    assert {example: len(score.results_of(example)) for example in kept} == {
        CatalaExample.FAMILY_BENEFITS: 16,
        CatalaExample.INHERITANCE: 4,
        CatalaExample.POLISH_TAXES: 8,
        CatalaExample.UNITED_STATES_TAX_CODE: 9,
        CatalaExample.NEW_SOUTH_WALES_COMMUNITY_GAMING: 25,
        CatalaExample.CROP_ROTATION: 5,
        CatalaExample.FIBRE_CONNECTION_GRANT: 1,
        CatalaExample.PERFORMING_ARTS_HIRING_GRANT: 1,
        CatalaExample.HOUSING_AIDS: 33,
    }


@pytest.mark.skipif(
    not all(test_file.path.exists() for test_file in IncomeTaxTestFile),
    reason="the income tax tests are fetched by scripts/fetch_catala_income_tax_tests.py",
)
def test_every_test_of_the_income_tax_is_reproduced() -> None:
    """
    The model reproduces every assertion of the 27 test scopes of ``impot_revenu``, CI
    fetching them.
    """
    score = CatalaScore.from_examples([CatalaExample.INCOME_TAX])
    assert [
        result.identifier for result in score.results if not result.is_reproduced
    ] == []
    assert len(score.results) == 27
