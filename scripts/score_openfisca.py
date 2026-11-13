"""
Prints the family benefits model's score on OpenFisca France's family allowance tests,
fetched beforehand by :file:`scripts/fetch_openfisca_tests.py`.

Run from the repository's root: ``python scripts/score_openfisca.py``.
"""

from __future__ import annotations

from law_as_code_benchmarks.openfisca.scoring import OpenFiscaScore

# %% score

if __name__ == "__main__":
    print(OpenFiscaScore.from_test_files().summary())
