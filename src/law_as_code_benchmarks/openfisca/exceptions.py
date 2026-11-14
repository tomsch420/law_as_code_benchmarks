"""
The exceptions of reading and answering OpenFisca France's tests.
"""

from __future__ import annotations

from dataclasses import dataclass

from krrood.exceptions import DataclassException

# %% reading tests


@dataclass
class UnexpectedOpenFiscaVariable(DataclassException):
    """
    An input or output of a test the reader does not know how to map onto the family
    benefits model.
    """

    test: str
    """The test's name."""

    variable: str
    """
    The variable's name.
    """

    def error_message(self) -> str:
        return f"Test {self.test!r} names {self.variable}, which the reader does not map onto the family benefits model."

    def suggest_correction(self) -> str:
        return "Check that the test is one of OpenFisca France's family allowance tests, or teach the reader the variable."


@dataclass
class PersonWithoutAge(DataclassException):
    """
    A person of a test given neither an age nor a birth date.
    """

    person: str
    """The person's name in the test."""

    def error_message(self) -> str:
        return f"Person {self.person} has neither an age nor a birth date."

    def suggest_correction(self) -> str:
        return "Give the person an age or a birth date, as every test of the family allowances does for a child."
