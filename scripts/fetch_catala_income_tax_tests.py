"""
Downloads the test files of Catala's impot_revenu example to
:file:`resources/catala_impot_revenu/`, which git ignores: the example is under the
CeCILL 2.1 licence, so its tests are not copied in.

Run from the repository's root: ``python scripts/fetch_catala_income_tax_tests.py``.
"""

from __future__ import annotations

from law_as_code_benchmarks.catala.income_tax.test_files import IncomeTaxTestFile

# %% fetch

if __name__ == "__main__":
    for test_file in IncomeTaxTestFile:
        test_file.fetch()
        print(f"fetched {test_file.path}")
