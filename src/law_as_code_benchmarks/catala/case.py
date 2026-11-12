"""
The tests of Catala's family benefits example: each test scope as a household and the
assertions it makes about it, read from the example's own files.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from law_as_code_benchmarks.catala.domain import (
    Child,
    ChildCare,
    Household,
    SchoolingStage,
    Territory,
)
from law_as_code_benchmarks.catala.entitlement import (
    FamilyBenefitEntitlementProvision,
)
from law_as_code_benchmarks.catala.exceptions import UnexpectedCatalaStatement
from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.reader import (
    Application,
    Assertion,
    CatalaDirectory,
    CatalaLanguage,
    CatalaTestReader,
    CatalaValue,
    Definition,
    FulfilledRule,
    Reference,
    ScopeBody,
    StructureLiteral,
)
from law_as_code_benchmarks.catala.scope_test import CatalaTest
from law_as_code_benchmarks.catala.supplements import FamilyAllowanceProvision


class CatalaTestFile(StrEnum):
    """The example's test files, each named after the directory of the example it comes from."""

    FAMILY_ALLOWANCES = "allocations_familiales.catala_fr"
    """The amounts of :file:`allocations_familiales/tests/tests_allocations_familiales.catala_fr`."""

    FAMILY_ALLOWANCES_ENTITLEMENT = "allocations_familiales_ouverture_droits.catala_fr"
    """The entitlement of :file:`allocations_familiales/tests/tests_ouverture_droits.catala_fr`."""

    FAMILY_BENEFITS_ENTITLEMENT = "prestations_familiales_ouverture_droits.catala_fr"
    """The entitlement of :file:`prestations_familiales/tests/tests_ouverture_droits.catala_fr`."""

    @property
    def path(self) -> Path:
        """Where the file is kept."""
        return CatalaDirectory.FAMILY_BENEFITS_TESTS / self.value


# %% Catala names


class ScopeVariable(StrEnum):
    """
    The variables of the scopes the tests define or assert, without the ``i_`` prefix
    of the interface of family allowances.
    """

    CHILDREN = "enfants"
    """The children in the household's charge."""

    RESOURCES = "ressources_ménage"
    """The household's resources."""

    ASSESSMENT_DATE = "date_courante"
    """The day the benefits are computed for."""

    RESIDENCE = "résidence"
    """Where the household lives."""

    CHILD_BEFORE_2012 = "avait_enfant_à_charge_avant_1er_janvier_2012"
    """Whether the household had a child in its charge before 2012."""

    AMOUNT_PAID = "montant_versé"
    """The family allowances paid."""

    ENTITLEMENT = "droit_ouvert"
    """Whether a child gives a right to family benefits."""


class ChildField(StrEnum):
    """
    The fields of the structures the tests describe a child with, without the ``d_``
    prefix of ``EnfantEntrée``.
    """

    IDENTIFIER = "identifiant"
    """The child's number."""

    BIRTH_DATE = "date_de_naissance"
    """The child's birth date."""

    MONTHLY_PAY = "rémuneration_mensuelle"
    """What the child earns in a month."""

    CARE = "prise_en_charge"
    """Who takes care of the child."""

    HAS_OPENED_FAMILY_ALLOWANCE = "a_déjà_ouvert_droit_aux_allocations_familiales"
    """Whether the child has given a right to family allowances before."""

    PERSONAL_HOUSING_AID = "bénéficie_titre_personnel_aide_personnelle_logement"
    """Whether the child receives housing aid in their own name."""

    SCHOOLING_STAGE = "obligation_scolaire"
    """Where the child stands to compulsory schooling."""


class CatalaPrefix(StrEnum):
    """The prefixes the interface of family allowances adds to the names it repeats."""

    INTERFACE = "i_"
    """Of the interface's variables."""

    INPUT_CHILD = "d_"
    """Of the fields of ``EnfantEntrée``."""


# %% children


@dataclass(frozen=True)
class ChildDescription:
    """A structure of the tests describing a child: ``EnfantEntrée``, ``Enfant`` or ``EnfantPrestationsFamiliales``."""

    structure: StructureLiteral
    """The structure."""

    def field_value(self, child_field: ChildField) -> CatalaValue | None:
        """:return: The value of *child_field*, with or without the ``d_`` prefix; None where the structure has no such field."""
        for name in (child_field.value, CatalaPrefix.INPUT_CHILD + child_field.value):
            if name in self.structure.fields:
                return self.structure.fields[name]
        return None

    def to_child(self) -> Child:
        """:return: The child the structure describes."""
        care = self.field_value(ChildField.CARE)
        stage = self.field_value(ChildField.SCHOOLING_STAGE)
        housing_aid = self.field_value(ChildField.PERSONAL_HOUSING_AID)
        return Child(
            identifier=self.field_value(ChildField.IDENTIFIER),
            birth_date=self.field_value(ChildField.BIRTH_DATE),
            monthly_pay=self.field_value(ChildField.MONTHLY_PAY),
            has_opened_family_allowance=self.field_value(
                ChildField.HAS_OPENED_FAMILY_ALLOWANCE
            ),
            care=None if care is None else ChildCare(care.last_part),
            receives_personal_housing_aid=bool(housing_aid),
            stated_schooling_stage=None
            if stage is None
            else SchoolingStage(stage.last_part),
        )


# %% the tests


@dataclass
class FamilyBenefitsAssertion(ABC):
    """What a test scope asserts about its household."""

    @abstractmethod
    def is_reproduced(self, household: Household) -> bool:
        """:return: Whether the model concludes about *household* what the assertion states."""


@dataclass
class AmountPaidAssertion(FamilyBenefitsAssertion):
    """That the family allowances paid to the household are an amount."""

    expected_amount: Money
    """The amount."""

    def is_reproduced(self, household: Household) -> bool:
        conclusions = FamilyAllowanceProvision(household=household).conclusions
        return [conclusion.amount for conclusion in conclusions] == [
            self.expected_amount
        ]


@dataclass
class EntitlementAssertion(FamilyBenefitsAssertion):
    """That a child gives, or does not give, a right to family benefits."""

    child: Child
    """The child."""

    expected_entitlement: bool
    """Whether the child gives the right."""

    def is_reproduced(self, household: Household) -> bool:
        conclusions = FamilyBenefitEntitlementProvision(household=household).conclusions
        return [
            conclusion.holds
            for conclusion in conclusions
            if conclusion.child is self.child
        ] == [self.expected_entitlement]


@dataclass
class FamilyBenefitsTest(CatalaTest):
    """A test scope of the example: a household and what it asserts about it."""

    test_file: CatalaTestFile
    """The file holding the test."""

    scope: str
    """The test scope's name."""

    household: Household
    """The household the test describes."""

    assertions: list[FamilyBenefitsAssertion] = field(default_factory=list)
    """What the test asserts."""

    @property
    def identifier(self) -> str:
        return f"{self.test_file.value}:{self.scope}"

    def is_reproduced(self) -> bool:
        return all(
            assertion.is_reproduced(self.household) for assertion in self.assertions
        )

    @classmethod
    def from_file(cls, test_file: CatalaTestFile) -> list[FamilyBenefitsTest]:
        """:return: The tests of *test_file*, in order."""
        return cls.from_text(test_file, test_file.path.read_text())

    @classmethod
    def from_text(
        cls, test_file: CatalaTestFile, text: str
    ) -> list[FamilyBenefitsTest]:
        """
        :param test_file: The file the tests are named after.
        :param text: A literate Catala test file.
        :return: The tests of *text*, in order.
        """
        program = CatalaTestReader(language=CatalaLanguage.FRENCH).read_program(text)
        data = {
            name: ChildDescription(
                structure=program.resolve(definition.value)
            ).to_child()
            for name, definition in program.data_definitions.items()
        }
        return [cls.from_scope(test_file, scope, data) for scope in program.test_scopes]

    @classmethod
    def from_scope(
        cls, test_file: CatalaTestFile, scope: ScopeBody, data: dict[str, Child]
    ) -> FamilyBenefitsTest:
        """
        :param test_file: The file holding the scope.
        :param scope: A test scope.
        :param data: The children the file's data scope defines, by variable name.
        :return: The test the scope states.
        """
        values = {}
        assertions = []
        for statement in scope.statements:
            match statement:
                case Definition() | FulfilledRule():
                    name = statement.target.last_part.removeprefix(
                        CatalaPrefix.INTERFACE
                    )
                    values[name] = (
                        statement.value if isinstance(statement, Definition) else True
                    )
                case Assertion():
                    assertions.append(cls.assertion_stated(scope, statement, data))
                case _:
                    raise UnexpectedCatalaStatement(
                        scope=scope.name, statement=statement
                    )
        children = [
            data[value.last_part]
            if isinstance(value, Reference)
            else ChildDescription(structure=value).to_child()
            for value in values.get(ScopeVariable.CHILDREN, [])
        ] or list(data.values())
        household = Household(
            assessment_date=values[ScopeVariable.ASSESSMENT_DATE],
            residence=Territory(values[ScopeVariable.RESIDENCE].last_part),
            children=children,
            resources=values.get(ScopeVariable.RESOURCES, Money.zero),
            had_child_before_2012=values.get(ScopeVariable.CHILD_BEFORE_2012, False),
        )
        return cls(
            test_file=test_file,
            scope=scope.name,
            household=household,
            assertions=assertions,
        )

    @staticmethod
    def assertion_stated(
        scope: ScopeBody, assertion: Assertion, data: dict[str, Child]
    ) -> FamilyBenefitsAssertion:
        """
        :return: What *assertion* of *scope* asserts: the amount paid, or a child's
            entitlement.
        :raises UnexpectedCatalaStatement: Where it asserts anything else.
        """
        expression, expected = assertion.asserted_value()
        match expression:
            case Reference() if (
                expression.last_part.removeprefix(CatalaPrefix.INTERFACE)
                == ScopeVariable.AMOUNT_PAID
            ):
                return AmountPaidAssertion(expected_amount=expected)
            case Application() if (
                expression.function.last_part == ScopeVariable.ENTITLEMENT
            ):
                return EntitlementAssertion(
                    child=data[expression.argument.last_part],
                    expected_entitlement=expected,
                )
        raise UnexpectedCatalaStatement(scope=scope.name, statement=assertion)
