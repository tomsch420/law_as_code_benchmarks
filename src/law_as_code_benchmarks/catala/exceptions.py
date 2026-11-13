"""
The exceptions of the model of Catala's family benefits.
"""

from __future__ import annotations

from dataclasses import dataclass

from krrood.exceptions import DataclassException
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
    from law_as_code_benchmarks.catala.domain import Child

# %% computing


@dataclass
class AmbiguousBirthday(DataclassException):
    """
    A birthday of a child born on February 29 that falls in a year without one.
    """

    child: Child
    """The child."""

    age: int
    """
    The age the birthday is for.
    """

    def error_message(self) -> str:
        return (
            f"Child {self.child.identifier}, born {self.child.birth_date}, has no "
            f"day to turn {self.age} on, the year having no February 29."
        )

    def suggest_correction(self) -> str:
        return "Decide whether the birthday falls on February 28 or March 1, as Catala asks a program to state."


# %% reading tests


@dataclass
class UnexpectedCatalaStatement(DataclassException):
    """
    A statement of a test scope the reader of the tests does not know how to apply.
    """

    scope: str
    """The scope holding it."""

    statement: object
    """
    The statement.
    """

    def error_message(self) -> str:
        return f"Test scope {self.scope} holds a statement the reader cannot apply: {self.statement}."

    def suggest_correction(self) -> str:
        return "Check that the test file is the Catala example's own, or teach the reader the statement."
