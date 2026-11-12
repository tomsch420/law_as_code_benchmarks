"""
The exceptions of the models of Catala's examples.
"""

from __future__ import annotations

import datetime
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


@dataclass
class UnmodelledScope(DataclassException):
    """
    A test asserting something of a scope no case of its example models.
    """

    scope: str
    """The scope's name."""

    def error_message(self) -> str:
        return f"A test asserts something of scope {self.scope}, which no case models."

    def suggest_correction(self) -> str:
        return "Add a case modelling the scope to the example's test file."


@dataclass
class AmbiguousConclusion(DataclassException):
    """
    A provision drawing several conclusions about a case where its variable has one
    value.
    """

    provision: type
    """The provision."""

    conclusions: list
    """
    Its conclusions.
    """

    def error_message(self) -> str:
        return f"{self.provision.__name__} drew {len(self.conclusions)} conclusions where one was expected: {self.conclusions}."

    def suggest_correction(self) -> str:
        return "Check that the provision's rule tree concludes once for each case, its default included."


@dataclass
class AmbiguousAnniversary(DataclassException):
    """
    A day some years after February 29 that falls in a year without one.
    """

    day: datetime.date
    """The day counted from."""

    years: int
    """
    The years counted.
    """

    def error_message(self) -> str:
        return f"{self.years} years after {self.day} has no day, the year having no February 29."

    def suggest_correction(self) -> str:
        return "Decide whether it falls on February 28 or March 1, as Catala asks a program to state."
