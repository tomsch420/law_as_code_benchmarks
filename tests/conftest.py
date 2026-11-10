"""
Fixtures shared by the tests of every benchmark.
"""

from __future__ import annotations

import shutil

import pytest

# %% SWI-Prolog


@pytest.fixture(scope="session")
def swipl() -> str:
    """
    The SWI-Prolog executable on the path; the tests needing it are skipped without it.
    """
    executable = shutil.which("swipl")
    if executable is None:
        pytest.skip("SWI-Prolog is not installed")
    return executable
