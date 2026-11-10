"""
The exceptions of the SARA benchmark's model.
"""

from __future__ import annotations

from dataclasses import dataclass

from krrood.exceptions import DataclassException
from typing_extensions import Any

# %% loading cases


@dataclass
class UnexpectedTestDirectives(DataclassException):
    """
    A case that does not test exactly one goal.
    """

    identifier: str
    """The case's identifier."""

    number_of_tests: int
    """
    How many test directives the case holds.
    """

    def error_message(self) -> str:
        return f"Case {self.identifier} holds {self.number_of_tests} test directives instead of one."

    def suggest_correction(self) -> str:
        return "Check that the case file is one of SARA's, unchanged."


# %% reading a case's world


@dataclass
class AmbiguousRole(DataclassException):
    """
    An event the case relates to more than one value in a role that takes one.
    """

    identifier: Any
    """The event's identifier."""

    role: str
    """
    The role.
    """

    def error_message(self) -> str:
        return f"The event {self.identifier} holds more than one value in the role {self.role}."

    def suggest_correction(self) -> str:
        return "Read the role's values as a list where the case may state several."
