"""
Tests of running SARA's own Prolog program on a case.
"""

from __future__ import annotations

from law_as_code_benchmarks.sara.reference import ReferenceRun

# %% the reference answer


def test_a_goal_autoloading_a_library_gets_the_reference_answer(swipl: str) -> None:
    """
    A test goal that autoloads one of SWI-Prolog's libraries, as ``sum_list`` does, still
    gets SARA's reference answer.
    """
    assert ReferenceRun.from_identifier("s3306_a_3_pos", swipl).passed
