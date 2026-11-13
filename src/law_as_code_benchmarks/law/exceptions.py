"""
The exceptions of the terms the models of every benchmark share.
"""

from __future__ import annotations

from dataclasses import dataclass

from krrood.exceptions import DataclassException

# %% fetched test files


@dataclass
class UnfetchedTestFile(DataclassException):
    """
    A test file a script fetches, which it has not fetched yet.
    """

    file_name: str
    """The file's name."""

    fetch_script: str
    """
    The script that fetches it, relative to the repository's root.
    """

    def error_message(self) -> str:
        return f"The test file {self.file_name} has not been fetched."

    def suggest_correction(self) -> str:
        return f"Run python {self.fetch_script} from the repository's root."
