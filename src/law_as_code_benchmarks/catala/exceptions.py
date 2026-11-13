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
    from law_as_code_benchmarks.catala.reader import Duration

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
    A test asserting something of, or calling, a scope no case of its example models.
    """

    scope: str
    """The scope's name."""

    def error_message(self) -> str:
        return f"A test asserts something of, or calls, scope {self.scope}, which no case models."

    def suggest_correction(self) -> str:
        return "Add a case modelling the scope to the example's test file."


@dataclass
class UnknownCatalaConstructor(DataclassException):
    """
    A constructor of a Catala enumeration that no subclass of the class the enumeration
    maps onto stands for.
    """

    enumeration: type
    """The class the enumeration maps onto."""

    constructor: str
    """
    The constructor's name.
    """

    def error_message(self) -> str:
        return f"No subclass of {self.enumeration.__name__} stands for Catala's constructor {self.constructor}."

    def suggest_correction(self) -> str:
        return "Add a subclass naming the constructor in its catala_constructor."


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
    A day some years and months after another that the calendar lacks, such as a year
    after February 29 or a month after January 31.
    """

    day: datetime.date
    """The day counted from."""

    duration: Duration
    """
    The duration counted.
    """

    def error_message(self) -> str:
        return f"{self.duration} after {self.day} has no day, the month it falls in being too short."

    def suggest_correction(self) -> str:
        return "Decide whether it falls on the month's last day or the next month's first, as Catala asks a program to state."


@dataclass
class DurationInDays(DataclassException):
    """
    A duration with days, read where a provision counts whole months, which Catala
    refuses to compare with months.
    """

    days: int
    """The days of the duration."""

    def error_message(self) -> str:
        return f"A duration of {self.days} days cannot be counted in whole months."

    def suggest_correction(self) -> str:
        return "State the duration in years and months, as the provision counts it."


@dataclass
class UncategorisedCrop(DataclassException):
    """
    A crop compared with another for the rotation that annex 4 of the crop rotation
    standard puts in no category, where Catala's example stops as impossible.
    """

    code: str
    """The crop's code."""

    def error_message(self) -> str:
        return f"Crop {self.code} is in no category of annex 4, so it cannot be compared with another for the rotation."

    def suggest_correction(self) -> str:
        return "Declare the crop with a code annex 4 lists."
