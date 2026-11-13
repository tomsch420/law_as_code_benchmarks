"""
Downloads OpenFisca France's family allowance tests to :file:`resources/openfisca/`,
which git ignores: OpenFisca France is under AGPL-3.0, so its tests are not copied in.

Run from the repository's root: ``python scripts/fetch_openfisca_tests.py``.
"""

from __future__ import annotations

from law_as_code_benchmarks.openfisca.yaml_test import OpenFiscaTestFile

# %% fetch

if __name__ == "__main__":
    for test_file in OpenFiscaTestFile:
        test_file.fetch()
        print(f"fetched {test_file.path}")
