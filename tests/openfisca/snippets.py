"""
Reads the test files of :file:`test_files`, written for these tests in the shape of
OpenFisca France's.
"""

from __future__ import annotations

from pathlib import Path

from law_as_code_benchmarks.openfisca.yaml_test import OpenFiscaTest, OpenFiscaTestFile

# %% snippets


def read_snippet(
    file_name: str, test_file: OpenFiscaTestFile = OpenFiscaTestFile.FAMILY_ALLOWANCES
) -> OpenFiscaTest:
    """:return: The one test of :file:`test_files/{file_name}`, named after *test_file*."""
    (test,) = test_file.tests_in(
        (Path(__file__).parent / "test_files" / file_name).read_text()
    )
    return test
