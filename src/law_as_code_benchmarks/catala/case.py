"""
The tests of Catala's family benefits example: each test scope as a household and the
assertions it makes about it, read from the example's own files.
"""

from __future__ import annotations

import datetime
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from functools import cache
from pathlib import Path

import pyparsing
from krrood.patterns.path_enumeration import PathEnumeration
from typing_extensions import TypeAlias

from law_as_code_benchmarks.catala.domain import (
    Child,
    ChildCare,
    Household,
    Money,
    SchoolingStage,
    Territory,
)
from law_as_code_benchmarks.catala.entitlement import (
    FamilyBenefitEntitlementProvision,
)
from law_as_code_benchmarks.catala.exceptions import UnexpectedCatalaStatement
from law_as_code_benchmarks.catala.supplements import FamilyAllowanceProvision

# %% files


class CatalaDirectory(PathEnumeration):
    """The files of Catala's family benefits example kept in the repository."""

    ROOT = Path(__file__).parents[3] / "resources" / "catala"
    """The directory holding them, with the example's license."""

    TESTS = ROOT / "tests"
    """The test files."""


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
        return CatalaDirectory.TESTS / self.value


# %% Catala names


class CatalaKeyword(StrEnum):
    """The words of Catala's French syntax the tests are written with."""

    DECLARATION = "déclaration"
    """Opens a declaration."""

    SCOPE = "champ d'application"
    """Names a scope."""

    DEFINITION = "définition"
    """Defines a variable."""

    RULE = "règle"
    """States a condition."""

    FULFILLED = "rempli"
    """Ends a rule that makes its condition hold."""

    ASSERTION = "assertion"
    """Asserts an expression."""

    EQUAL_TO = "égal à"
    """Separates a defined variable from its value."""

    NOT = "non"
    """Negates an expression."""

    OF = "de"
    """Applies a function variable to an argument."""

    TRUE = "vrai"
    """True."""

    FALSE = "faux"
    """False."""

    TEST_ATTRIBUTE = "#[test]"
    """Marks a test scope."""


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


# %% values read from the files


@dataclass(frozen=True)
class Reference:
    """A dotted name: a variable of another scope, an enumeration's constructor or a scope's variable."""

    parts: tuple[str, ...]
    """The name's parts, in order."""

    @property
    def last_part(self) -> str:
        """The last part, which names the variable or constructor without the prefixes leading to it."""
        return self.parts[-1]


@dataclass(frozen=True)
class StructureLiteral:
    """A structure written out field by field."""

    structure: Reference
    """The structure's name."""

    fields: dict[str, CatalaValue]
    """The value of each field, by name."""

    def field_value(self, child_field: ChildField) -> CatalaValue | None:
        """:return: The value of *child_field*, with or without the ``d_`` prefix; None where the structure has no such field."""
        for name in (child_field.value, CatalaPrefix.INPUT_CHILD + child_field.value):
            if name in self.fields:
                return self.fields[name]
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


CatalaValue: TypeAlias = (
    Money | datetime.date | int | bool | Reference | StructureLiteral | list
)
"""A value as the tests write it."""


@dataclass(frozen=True)
class Definition:
    """``définition target égal à value``."""

    target: Reference
    """The variable defined."""

    value: CatalaValue
    """Its value."""


@dataclass(frozen=True)
class FulfilledRule:
    """``règle target rempli``: a condition that holds."""

    target: Reference
    """The condition."""


@dataclass(frozen=True)
class Equality:
    """``assertion target = value``."""

    target: Reference
    """The variable asserted."""

    value: CatalaValue
    """The value it is asserted to equal."""


@dataclass(frozen=True)
class Application:
    """``assertion (target de argument)``, or its negation with ``non``."""

    target: Reference
    """The function variable applied."""

    argument: Reference
    """What it is applied to."""

    holds: bool
    """Whether the application is asserted to hold, false under ``non``."""


Statement: TypeAlias = Definition | FulfilledRule | Equality | Application
"""A statement of a scope's body."""


@dataclass(frozen=True)
class ScopeBody:
    """The statements of a scope, and whether it is a test."""

    name: str
    """The scope's name."""

    statements: list[Statement]
    """Its statements, in order."""

    is_test: bool = False
    """Whether it is a test scope."""


# %% reading the files


@dataclass
class CatalaTestReader:
    """
    Reads the Catala code blocks of a test file: its scope bodies, declarations left
    out, in the subset of Catala the example's tests are written in.
    """

    def read_scopes(self, text: str) -> list[ScopeBody]:
        """
        :param text: A literate Catala file.
        :return: The bodies of the scopes its Catala code blocks define, each marked a
            test where the file declares it one.
        """
        code = "\n".join(re.findall(r"```catala\n(.*?)```", text, flags=re.DOTALL))
        test_names = set(
            re.findall(
                re.escape(CatalaKeyword.TEST_ATTRIBUTE)
                + r"\s*"
                + CatalaKeyword.DECLARATION
                + r"\s+"
                + CatalaKeyword.SCOPE
                + r"\s+(\w+)",
                code,
            )
        )
        return [
            ScopeBody(
                name=body.name,
                statements=body.statements,
                is_test=body.name in test_names,
            )
            for body in self.file_grammar().parse_string(code, parse_all=True)
        ]

    @classmethod
    @cache
    def value_grammar(cls) -> pyparsing.ParserElement:
        """The grammar of a value."""
        value = pyparsing.Forward()
        name = pyparsing.Regex(r"[^\W\d]\w*")
        reference = pyparsing.DelimitedList(name, ".", combine=False).set_parse_action(
            lambda tokens: Reference(parts=tuple(tokens))
        )
        money = pyparsing.Regex(r"\d[\d ]*(,\d+)?\s*€").set_parse_action(
            lambda tokens: Money.from_euros(
                Decimal(tokens[0].rstrip("€").replace(" ", "").replace(",", "."))
            )
        )
        date = pyparsing.Regex(r"\|\d{4}-\d{2}-\d{2}\|").set_parse_action(
            lambda tokens: datetime.date.fromisoformat(tokens[0].strip("|"))
        )
        integer = pyparsing.Regex(r"-?\d+").set_parse_action(
            lambda tokens: int(tokens[0])
        )
        boolean = (
            pyparsing.Keyword(CatalaKeyword.TRUE)
            | pyparsing.Keyword(CatalaKeyword.FALSE)
        ).set_parse_action(lambda tokens: tokens[0] == CatalaKeyword.TRUE)
        field_value = pyparsing.Group(
            pyparsing.Suppress("--") + name + pyparsing.Suppress(":") + value
        )
        structure = (
            reference
            + pyparsing.Suppress("{")
            + pyparsing.Group(pyparsing.ZeroOrMore(field_value))
            + pyparsing.Suppress("}")
        ).set_parse_action(
            lambda tokens: StructureLiteral(
                structure=tokens[0],
                fields={
                    field_name: field_value for field_name, field_value in tokens[1]
                },
            )
        )
        catala_list = (
            pyparsing.Suppress("[")
            + pyparsing.Group(pyparsing.ZeroOrMore(value + pyparsing.Suppress(";")))
            + pyparsing.Suppress("]")
        ).set_parse_action(lambda tokens: [tokens[0].as_list()])
        value <<= money | date | integer | boolean | catala_list | structure | reference
        return value

    @classmethod
    @cache
    def file_grammar(cls) -> pyparsing.ParserElement:
        """The grammar of a file's Catala code, comments and declarations left out."""
        value = cls.value_grammar()
        name = pyparsing.Regex(r"[^\W\d]\w*")
        reference = pyparsing.DelimitedList(name, ".", combine=False).set_parse_action(
            lambda tokens: Reference(parts=tuple(tokens))
        )
        scope_keyword = pyparsing.Literal(CatalaKeyword.SCOPE)
        declaration = pyparsing.Suppress(
            pyparsing.Opt(pyparsing.Literal(CatalaKeyword.TEST_ATTRIBUTE))
            + pyparsing.Keyword(CatalaKeyword.DECLARATION)
            + scope_keyword
            + name
            + ":"
            + pyparsing.ZeroOrMore(
                (
                    pyparsing.Keyword("résultat")
                    + name
                    + pyparsing.Keyword("contenu")
                    + reference
                )
                | (name + scope_keyword + reference)
            )
        )
        definition = (
            pyparsing.Suppress(pyparsing.Keyword(CatalaKeyword.DEFINITION))
            + reference
            + pyparsing.Suppress(pyparsing.Literal(CatalaKeyword.EQUAL_TO))
            + value
        ).set_parse_action(lambda tokens: Definition(target=tokens[0], value=tokens[1]))
        rule = (
            pyparsing.Suppress(pyparsing.Keyword(CatalaKeyword.RULE))
            + reference
            + pyparsing.Suppress(pyparsing.Keyword(CatalaKeyword.FULFILLED))
        ).set_parse_action(lambda tokens: FulfilledRule(target=tokens[0]))
        application = (
            pyparsing.Suppress("(")
            + reference
            + pyparsing.Suppress(pyparsing.Keyword(CatalaKeyword.OF))
            + reference
            + pyparsing.Suppress(")")
        )
        positive_application = application.copy().set_parse_action(
            lambda tokens: Application(target=tokens[0], argument=tokens[1], holds=True)
        )
        negative_application = (
            pyparsing.Suppress("(")
            + pyparsing.Suppress(pyparsing.Keyword(CatalaKeyword.NOT))
            + application
            + pyparsing.Suppress(")")
        ).set_parse_action(
            lambda tokens: Application(
                target=tokens[0], argument=tokens[1], holds=False
            )
        )
        equality = (reference + pyparsing.Suppress("=") + value).set_parse_action(
            lambda tokens: Equality(target=tokens[0], value=tokens[1])
        )
        assertion = pyparsing.Suppress(pyparsing.Keyword(CatalaKeyword.ASSERTION)) + (
            negative_application | positive_application | equality
        )
        body = (
            pyparsing.Suppress(scope_keyword)
            + name
            + pyparsing.Suppress(":")
            + pyparsing.Group(pyparsing.ZeroOrMore(definition | rule | assertion))
        ).set_parse_action(
            lambda tokens: ScopeBody(name=tokens[0], statements=tokens[1].as_list())
        )
        grammar = pyparsing.ZeroOrMore(declaration | body)
        grammar.ignore(pyparsing.Regex(r"#(?!\[test\]).*"))
        return grammar


# %% the tests


@dataclass
class CatalaAssertion(ABC):
    """What a test scope asserts about its household."""

    @abstractmethod
    def is_reproduced(self, household: Household) -> bool:
        """:return: Whether the model concludes about *household* what the assertion states."""


@dataclass
class AmountPaidAssertion(CatalaAssertion):
    """That the family allowances paid to the household are an amount."""

    expected_amount: Money
    """The amount."""

    def is_reproduced(self, household: Household) -> bool:
        conclusions = FamilyAllowanceProvision(household=household).conclusions
        return [conclusion.amount for conclusion in conclusions] == [
            self.expected_amount
        ]


@dataclass
class EntitlementAssertion(CatalaAssertion):
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
class CatalaTest:
    """A test scope of the example: a household and what it asserts about it."""

    test_file: CatalaTestFile
    """The file holding the test."""

    scope: str
    """The test scope's name."""

    household: Household
    """The household the test describes."""

    assertions: list[CatalaAssertion] = field(default_factory=list)
    """What the test asserts."""

    @property
    def identifier(self) -> str:
        """The test's file and scope, which name it uniquely."""
        return f"{self.test_file.value}:{self.scope}"

    def is_reproduced(self) -> bool:
        """:return: Whether the model concludes everything the test asserts."""
        return all(
            assertion.is_reproduced(self.household) for assertion in self.assertions
        )

    @classmethod
    def from_file(cls, test_file: CatalaTestFile) -> list[CatalaTest]:
        """:return: The tests of *test_file*, in order."""
        return cls.from_text(test_file, test_file.path.read_text())

    @classmethod
    def from_text(cls, test_file: CatalaTestFile, text: str) -> list[CatalaTest]:
        """
        :param test_file: The file the tests are named after.
        :param text: A literate Catala test file.
        :return: The tests of *text*, in order.
        """
        scopes = CatalaTestReader().read_scopes(text)
        data = {
            definition.target.last_part: definition.value.to_child()
            for scope in scopes
            if not scope.is_test
            for definition in scope.statements
        }
        return [
            cls.from_scope(test_file, scope, data) for scope in scopes if scope.is_test
        ]

    @classmethod
    def from_scope(
        cls, test_file: CatalaTestFile, scope: ScopeBody, data: dict[str, Child]
    ) -> CatalaTest:
        """
        :param test_file: The file holding the scope.
        :param scope: A test scope.
        :param data: The children the file's data scope defines, by variable name.
        :return: The test the scope states.
        """
        values = {}
        assertions = []
        for statement in scope.statements:
            name = statement.target.last_part.removeprefix(CatalaPrefix.INTERFACE)
            match statement:
                case Definition():
                    values[name] = statement.value
                case FulfilledRule():
                    values[name] = True
                case Equality() if name == ScopeVariable.AMOUNT_PAID:
                    assertions.append(
                        AmountPaidAssertion(expected_amount=statement.value)
                    )
                case Application() if name == ScopeVariable.ENTITLEMENT:
                    assertions.append(
                        EntitlementAssertion(
                            child=data[statement.argument.last_part],
                            expected_entitlement=statement.holds,
                        )
                    )
                case _:
                    raise UnexpectedCatalaStatement(
                        scope=scope.name, statement=statement
                    )
        children = [
            data[value.last_part] if isinstance(value, Reference) else value.to_child()
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
