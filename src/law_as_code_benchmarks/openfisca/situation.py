"""
The situation an OpenFisca test describes - persons, the family they form and where it
lives - mirrored from the test's YAML and mapped onto the family benefits'
:class:`~law_as_code_benchmarks.catala.domain.Household`.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import StrEnum
from fractions import Fraction

from krrood.ormatic.utils import classproperty
from typing_extensions import Any

from law_as_code_benchmarks.catala.domain import (
    Child,
    ChildCare,
    Household,
    Territory,
)
from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.openfisca.arithmetic import ArithmeticReader
from law_as_code_benchmarks.openfisca.exceptions import (
    PersonWithoutAge,
    UnexpectedOpenFiscaVariable,
)

# %% OpenFisca names


class OpenFiscaEntity(StrEnum):
    """The entities a test's input describes, each spelled as OpenFisca France names it."""

    PERSONS = "individus"
    """The persons, by name."""

    FAMILY = "famille"
    """The family, which family benefits are paid to."""

    TAX_HOUSEHOLD = "foyer_fiscal"
    """The tax household, which repeats the family's members."""

    DWELLING = "menage"
    """The dwelling the family lives in."""


class FamilyRole(StrEnum):
    """The roles of a family's members."""

    PARENTS = "parents"
    """The parents."""

    CHILDREN = "enfants"
    """The children."""


class DwellingVariable(StrEnum):
    """The variables and roles of a test's dwelling."""

    REFERENCE_PERSON = "personne_de_reference"
    """The dwelling's reference person, a role."""

    SPOUSE = "conjoint"
    """The reference person's spouse, a role."""

    CHILDREN = "enfants"
    """The children living there, a role."""

    OVERSEAS = "residence_dom"
    """Whether the dwelling is in an overseas department."""

    MAYOTTE = "residence_mayotte"
    """Whether the dwelling is in Mayotte."""


class PersonVariable(StrEnum):
    """The variables of a person the tests set."""

    AGE = "age"
    """The person's age in whole years on the test's month."""

    BIRTH_DATE = "date_naissance"
    """The person's birth date."""

    SHARED_RESIDENCE = "garde_alternee"
    """Whether the child lives with each parent in turn."""

    WAGES = "revenu_assimile_salaire"
    """The person's income treated as wages, by year."""


# %% persons


@dataclass(frozen=True)
class Person:
    """A person of a test."""

    name: str
    """The person's name in the test."""

    age: int | None = None
    """The person's age on the test's month; None where the test gives a birth date instead."""

    birth_date: datetime.date | None = None
    """The person's birth date; None where the test gives an age instead."""

    shared_residence: bool = False
    """Whether the person, a child, lives with each parent in turn."""

    yearly_wages: dict[int, Fraction] = field(default_factory=dict)
    """The person's income treated as wages, by calendar year."""

    @classmethod
    def from_json(cls, test: str, name: str, json: dict[str, Any]) -> Person:
        """
        :param test: The name of the test describing the person.
        :param name: The person's name in the test.
        :param json: The person's variables as the test sets them.
        :return: The person.
        :raises UnexpectedOpenFiscaVariable: Where the test sets a variable the reader
            does not map.
        """
        for variable in json:
            if variable not in PersonVariable:
                raise UnexpectedOpenFiscaVariable(test=test, variable=variable)
        birth_date = json.get(PersonVariable.BIRTH_DATE)
        return cls(
            name=name,
            age=json.get(PersonVariable.AGE),
            birth_date=None
            if birth_date is None
            else datetime.date.fromisoformat(str(birth_date)),
            shared_residence=json.get(PersonVariable.SHARED_RESIDENCE, False),
            yearly_wages={
                int(year): ArithmeticReader().read(wages)
                for year, wages in json.get(PersonVariable.WAGES, {}).items()
            },
        )

    def birth_date_for(self, day: datetime.date) -> datetime.date:
        """
        :return: The person's birth date; where the test gives an age instead, the day
            the person turned that age, taken to be *day* that many years earlier.
        :raises PersonWithoutAge: Where the test gives neither.
        """
        if self.birth_date is not None:
            return self.birth_date
        if self.age is None:
            raise PersonWithoutAge(person=self.name)
        return day.replace(year=day.year - self.age)


# %% the situation


@dataclass(frozen=True)
class Situation:
    """The persons a test describes, the family they form and where it lives."""

    persons: dict[str, Person]
    """The persons, by name."""

    parents: list[str]
    """The names of the family's parents."""

    children: list[str]
    """The names of the family's children, in the test's order."""

    overseas: bool = False
    """Whether the family lives in an overseas department."""

    in_mayotte: bool = False
    """Whether the family lives in Mayotte."""

    @classproperty
    def professional_expenses_deduction(cls) -> Fraction:
        """
        The share of wages article 83 of the Code général des impôts deducts for
        professional expenses, 10 %, its floor and ceiling not modelled.
        """
        return Fraction(1, 10)

    @classproperty
    def years_before_reference_year(cls) -> int:
        """
        How many years before the assessment's year resources are counted for, two,
        as R532-3 of the Code de la sécurité sociale counts them.
        """
        return 2

    @classproperty
    def overseas_territory(cls) -> Territory:
        """
        The territory a family OpenFisca places in an overseas department other than
        Mayotte lives in, Guadeloupe; the model treats every such department alike.
        """
        return Territory.GUADELOUPE

    @classmethod
    def from_json(cls, test: str, json: dict[str, Any]) -> Situation:
        """
        :param test: The name of the test describing the situation.
        :param json: The test's input.
        :return: The situation.
        :raises UnexpectedOpenFiscaVariable: Where the input sets a variable the
            reader does not map.
        """
        for entity in json:
            if entity not in OpenFiscaEntity:
                raise UnexpectedOpenFiscaVariable(test=test, variable=entity)
        family = json[OpenFiscaEntity.FAMILY]
        for role in family:
            if role not in FamilyRole:
                raise UnexpectedOpenFiscaVariable(test=test, variable=role)
        dwelling = json.get(OpenFiscaEntity.DWELLING, {})
        for variable in dwelling:
            if variable not in DwellingVariable:
                raise UnexpectedOpenFiscaVariable(test=test, variable=variable)
        return cls(
            persons={
                name: Person.from_json(test, name, variables or {})
                for name, variables in json[OpenFiscaEntity.PERSONS].items()
            },
            parents=family[FamilyRole.PARENTS],
            children=family.get(FamilyRole.CHILDREN, []),
            overseas=dwelling.get(DwellingVariable.OVERSEAS, False),
            in_mayotte=dwelling.get(DwellingVariable.MAYOTTE, False),
        )

    def to_household(self, day: datetime.date) -> Household:
        """
        :return: The household the situation describes, assessed on *day*: every child
            in its charge, cared for in shared residence where the test says so.
        """
        return Household(
            assessment_date=day,
            residence=self.territory,
            children=[
                self.child(index, self.persons[name], day)
                for index, name in enumerate(self.children)
            ],
            resources=self.resources_for(day.year),
        )

    @property
    def territory(self) -> Territory:
        """Where the family lives."""
        if self.in_mayotte:
            return Territory.MAYOTTE
        if self.overseas:
            return self.overseas_territory
        return Territory.METROPOLITAN_FRANCE

    def resources_for(self, year: int) -> Money:
        """
        :return: The parents' resources for *year*: their wages of the reference year,
            less the deduction for professional expenses.
        """
        wages = sum(
            self.persons[name].yearly_wages.get(
                year - self.years_before_reference_year, Fraction(0)
            )
            for name in self.parents
        )
        return Money.from_euros(1) * (
            wages * (1 - self.professional_expenses_deduction)
        )

    @staticmethod
    def child(index: int, person: Person, day: datetime.date) -> Child:
        """
        :return: *person* as the child numbered *index* plus one, earning nothing and
            taken to have given the household a right to family allowances before.
        """
        return Child(
            identifier=index + 1,
            birth_date=person.birth_date_for(day),
            monthly_pay=Money.zero,
            has_opened_family_allowance=True,
            care=ChildCare.SHARED_RESIDENCE_SHARED_ALLOWANCE
            if person.shared_residence
            else ChildCare.EFFECTIVE_AND_PERMANENT,
        )
