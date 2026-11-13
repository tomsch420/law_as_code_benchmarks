"""
Tests of scoring the models on the tests of the Catala examples.
"""

from __future__ import annotations

from law_as_code_benchmarks.catala.scoring import CatalaExample, CatalaScore

# %% the score


def test_every_test_of_every_example_is_reproduced() -> None:
    """
    The models reproduce every assertion of all 102 test scopes: 16 of the family
    benefits, 4 of inheritance, 8 of the Polish tax, 9 of the US tax code, 25 of New
    South Wales' gaming, 5 of the crop rotation standard, 1 of the fibre grant, 1 of the
    hiring grant and 33 of the housing aids.
    """
    score = CatalaScore.from_examples()
    assert [
        result.identifier for result in score.results if not result.is_reproduced
    ] == []
    assert {example: len(score.results_of(example)) for example in CatalaExample} == {
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
