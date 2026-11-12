"""
Prints the model's score on the tests of Catala's family benefits example.

Run from the repository's root: ``python scripts/score_catala.py``.
"""

from __future__ import annotations

from law_as_code_benchmarks.catala.scoring import CatalaScore

# %% score

if __name__ == "__main__":
    print(CatalaScore.from_test_files().summary())
