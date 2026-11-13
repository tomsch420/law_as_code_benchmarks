"""
Reads the test files of Catala's examples, in the subset of Catala their tests are
written in, French, English or Polish: the scopes they define, the values and
assertions of each, and the subscopes a test scope declares.
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from functools import cache
from pathlib import Path

import pyparsing
from krrood.patterns.path_enumeration import PathEnumeration
from typing_extensions import TypeAlias

from law_as_code_benchmarks.catala.money import Money

# %% files


class CatalaDirectory(PathEnumeration):
    """The files of Catala's examples kept in the repository."""

    ROOT = Path(__file__).parents[3] / "resources" / "catala"
    """The directory holding them, with the examples' license."""

    FAMILY_BENEFITS_TESTS = ROOT / "tests"
    """The test files of the family benefits example."""


# %% languages


@dataclass(frozen=True)
class CatalaKeywords:
    """The words a language of Catala writes the constructs of test files with."""

    declaration: str
    """Opens a declaration."""

    scope: str
    """Names a scope."""

    definition: str
    """Defines a variable."""

    equal_to: str
    """Separates a defined variable from its value."""

    rule: str | None
    """States a condition; None where no test file of the language uses it."""

    fulfilled: str | None
    """Ends a rule that makes its condition hold; None where no test file of the language uses it."""

    assertion: str
    """Asserts an expression."""

    negation: str | None
    """Negates an expression; None where no test file of the language uses it."""

    application: str | None
    """Applies a function to an argument; None where no test file of the language uses it."""

    content: str | None
    """Gives an enumeration's constructor its content; None where no test file of the language uses it."""

    true: str
    """True."""

    false: str
    """False."""


class CatalaLanguage(Enum):
    """The languages Catala is written in, each worth its keywords."""

    FRENCH = CatalaKeywords(
        declaration="déclaration",
        scope="champ d'application",
        definition="définition",
        equal_to="égal à",
        rule="règle",
        fulfilled="rempli",
        assertion="assertion",
        negation="non",
        application="de",
        content="contenu",
        true="vrai",
        false="faux",
    )
    """French, of files ending in ``.catala_fr``."""

    ENGLISH = CatalaKeywords(
        declaration="declaration",
        scope="scope",
        definition="definition",
        equal_to="equals",
        rule="rule",
        fulfilled="fulfilled",
        assertion="assertion",
        negation="not",
        application="of",
        content="content",
        true="true",
        false="false",
    )
    """English, of files ending in ``.catala_en``."""

    POLISH = CatalaKeywords(
        declaration="deklaracja",
        scope="zakres",
        definition="definicja",
        equal_to="wynosi",
        rule=None,
        fulfilled=None,
        assertion="asercja",
        negation=None,
        application=None,
        content=None,
        true="prawda",
        false="fałsz",
    )
    """Polish, of files ending in ``.catala_pl``."""

    @classmethod
    def from_path(cls, path: Path) -> CatalaLanguage:
        """:return: The language of the Catala file at *path*, by its suffix."""
        return {
            ".catala_fr": cls.FRENCH,
            ".catala_en": cls.ENGLISH,
            ".catala_pl": cls.POLISH,
        }[path.suffix]


# %% values


@dataclass(frozen=True)
class Reference:
    """A dotted name: a scope's variable, a variable of a data scope or an enumeration's constructor."""

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


@dataclass(frozen=True)
class ConstructorWithContent:
    """An enumeration's constructor given its content, as ``Constructor content value``."""

    constructor: Reference
    """The constructor."""

    content: CatalaValue
    """Its content."""


@dataclass(frozen=True)
class Application:
    """A function applied to an argument, as ``function of argument``."""

    function: Reference
    """The function."""

    argument: CatalaValue
    """The argument."""


@dataclass(frozen=True)
class Negation:
    """An expression negated, as ``not expression``."""

    operand: CatalaValue
    """The expression negated."""


CatalaValue: TypeAlias = (
    Money
    | Fraction
    | datetime.date
    | int
    | bool
    | Reference
    | StructureLiteral
    | ConstructorWithContent
    | Application
    | Negation
    | list
)
"""A value or expression as the tests write it."""


# %% statements


@dataclass(frozen=True)
class Definition:
    """``definition target equals value``, or a function's with ``definition target of parameter``."""

    target: Reference
    """The variable defined."""

    value: CatalaValue
    """Its value."""

    parameter: str | None = None
    """The parameter of a function defined; None for a plain variable."""


@dataclass(frozen=True)
class FulfilledRule:
    """``rule target fulfilled``: a condition that holds."""

    target: Reference
    """The condition."""


@dataclass(frozen=True)
class Assertion:
    """``assertion expression``, or ``assertion expression = expected``."""

    expression: CatalaValue
    """The expression asserted."""

    expected: CatalaValue | None = None
    """The value it is asserted to equal; None where the expression is asserted to hold."""

    def asserted_value(self) -> tuple[CatalaValue, CatalaValue]:
        """:return: The expression asserted, any negation removed, and the value it is asserted to have: ``expected``, or whether it holds."""
        if self.expected is not None:
            return self.expression, self.expected
        if isinstance(self.expression, Negation):
            return self.expression.operand, False
        return self.expression, True


Statement: TypeAlias = Definition | FulfilledRule | Assertion
"""A statement of a scope's body."""


@dataclass(frozen=True)
class ScopeBody:
    """The statements of a scope, whether it is a test, and the subscopes it declares."""

    name: str
    """The scope's name."""

    statements: list[Statement]
    """Its statements, in order."""

    is_test: bool = False
    """Whether it is a test scope."""

    subscopes: dict[str, str] = field(default_factory=dict)
    """The scope each declared subscope is of, by subscope name, without the module prefix."""


# %% programs


@dataclass
class CatalaProgram:
    """The scopes of a test file, read."""

    scopes: list[ScopeBody]
    """The scopes, in order."""

    @property
    def test_scopes(self) -> list[ScopeBody]:
        """The test scopes, in order."""
        return [scope for scope in self.scopes if scope.is_test]

    @property
    def data_definitions(self) -> dict[str, Definition]:
        """The definitions of the scopes that are no test, by the name of the variable defined."""
        return {
            statement.target.last_part: statement
            for scope in self.scopes
            if not scope.is_test
            for statement in scope.statements
            if isinstance(statement, Definition)
        }

    def resolve(self, value: CatalaValue) -> CatalaValue:
        """:return: *value* with every variable of a data scope, and every function of one applied, replaced by its value."""
        definitions = self.data_definitions
        match value:
            case Reference() if value.last_part in definitions:
                return self.resolve(definitions[value.last_part].value)
            case Application() if value.function.last_part in definitions:
                return self.resolve(definitions[value.function.last_part].value)
            case StructureLiteral():
                return StructureLiteral(
                    structure=value.structure,
                    fields={
                        name: self.resolve(field_value)
                        for name, field_value in value.fields.items()
                    },
                )
            case ConstructorWithContent():
                return ConstructorWithContent(
                    constructor=value.constructor, content=self.resolve(value.content)
                )
            case list():
                return [self.resolve(element) for element in value]
        return value


# %% reading


@dataclass(frozen=True)
class CatalaTestReader:
    """Reads the Catala code blocks of a test file in one language of Catala."""

    language: CatalaLanguage
    """The language the file is written in."""

    def read_program(self, text: str) -> CatalaProgram:
        """
        :param text: A literate Catala file.
        :return: The scopes its Catala code blocks define, declarations read only for
            which scopes are tests and which subscopes each declares.
        """
        code = "\n".join(
            re.findall(r"```catala(?:-metadata)?\n(.*?)```", text, flags=re.DOTALL)
        )
        keywords = self.language.value
        declarations = re.findall(
            rf"^(#\[test\]\s*)?{re.escape(keywords.declaration)}\s+"
            rf"{re.escape(keywords.scope)}\s+(\w+)\s*:\s*\n((?:[ \t]+\S.*\n?)*)",
            code,
            flags=re.MULTILINE,
        )
        test_names = {name for attribute, name, _ in declarations if attribute}
        subscopes = {
            name: dict(
                re.findall(
                    rf"^\s+(\w+)\s+{re.escape(keywords.scope)}\s+(?:\w+\.)*(\w+)\s*$",
                    members,
                    flags=re.MULTILINE,
                )
            )
            for _, name, members in declarations
        }
        body = re.sub(
            rf"^(#\[test\]\s*)?{re.escape(keywords.declaration)}\b.*\n(?:[ \t]+\S.*\n?)*",
            "",
            code,
            flags=re.MULTILINE,
        )
        return CatalaProgram(
            scopes=[
                ScopeBody(
                    name=scope.name,
                    statements=scope.statements,
                    is_test=scope.name in test_names,
                    subscopes=subscopes.get(scope.name, {}),
                )
                for scope in self.program_grammar(self.language).parse_string(
                    body, parse_all=True
                )
            ]
        )

    @staticmethod
    def keyword(word: str) -> pyparsing.ParserElement:
        """:return: The grammar of *word*, matched as a whole word or phrase."""
        return pyparsing.Regex(rf"{re.escape(word)}(?!\w)")

    @staticmethod
    def money_from_text(text: str) -> Money:
        """:return: The money *text* writes: ``$1,500.00``, ``30 000,50 €`` or ``100 PLN``."""
        if text.startswith("$"):
            digits = text[1:].replace(",", "")
        else:
            digits = re.sub(r"\s*(€|PLN)$", "", text).replace(" ", "").replace(",", ".")
        return Money.from_euros(Decimal(digits))

    @classmethod
    @cache
    def expression_grammar(cls, language: CatalaLanguage) -> pyparsing.ParserElement:
        """The grammar of a value or expression in *language*."""
        keywords = language.value
        expression = pyparsing.Forward()
        name = pyparsing.Regex(r"[^\W\d]\w*")
        reference = pyparsing.DelimitedList(name, ".", combine=False).set_parse_action(
            lambda tokens: Reference(parts=tuple(tokens))
        )
        money = pyparsing.Regex(
            r"\$\d[\d,]*(\.\d+)?|\d[\d ]*(,\d+)?\s*€|\d[\d ]*([.,]\d+)?\s*PLN"
        ).set_parse_action(lambda tokens: cls.money_from_text(tokens[0]))
        date = pyparsing.Regex(r"\|\d{4}-\d{2}-\d{2}\|").set_parse_action(
            lambda tokens: datetime.date.fromisoformat(tokens[0].strip("|"))
        )
        decimal = pyparsing.Regex(r"-?\d+[.,]\d+").set_parse_action(
            lambda tokens: Fraction(tokens[0].replace(",", "."))
        )
        integer = pyparsing.Regex(r"-?\d+").set_parse_action(
            lambda tokens: int(tokens[0])
        )
        boolean = (
            cls.keyword(keywords.true) | cls.keyword(keywords.false)
        ).set_parse_action(lambda tokens: tokens[0] == keywords.true)
        field_value = pyparsing.Group(
            pyparsing.Suppress("--") + name + pyparsing.Suppress(":") + expression
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
            + pyparsing.Group(
                pyparsing.ZeroOrMore(expression + pyparsing.Suppress(";"))
            )
            + pyparsing.Suppress("]")
        ).set_parse_action(lambda tokens: [tokens[0].as_list()])
        parenthesized = pyparsing.Suppress("(") + expression + pyparsing.Suppress(")")
        primary = (
            money
            | date
            | decimal
            | integer
            | boolean
            | catala_list
            | structure
            | parenthesized
        )
        alternatives = []
        if keywords.content is not None:
            alternatives.append(
                (
                    reference
                    + pyparsing.Suppress(cls.keyword(keywords.content))
                    + expression
                ).set_parse_action(
                    lambda tokens: ConstructorWithContent(
                        constructor=tokens[0], content=tokens[1]
                    )
                )
            )
        if keywords.application is not None:
            alternatives.append(
                (
                    reference
                    + pyparsing.Suppress(cls.keyword(keywords.application))
                    + expression
                ).set_parse_action(
                    lambda tokens: Application(function=tokens[0], argument=tokens[1])
                )
            )
        if keywords.negation is not None:
            alternatives.append(
                (
                    pyparsing.Suppress(cls.keyword(keywords.negation)) + expression
                ).set_parse_action(lambda tokens: Negation(operand=tokens[0]))
            )
        expression <<= pyparsing.MatchFirst(alternatives + [primary, reference])
        return expression

    @classmethod
    @cache
    def program_grammar(cls, language: CatalaLanguage) -> pyparsing.ParserElement:
        """The grammar of the scope bodies of a file in *language*, declarations removed and comments left out."""
        keywords = language.value
        expression = cls.expression_grammar(language)
        name = pyparsing.Regex(r"[^\W\d]\w*")
        reference = pyparsing.DelimitedList(name, ".", combine=False).set_parse_action(
            lambda tokens: Reference(parts=tuple(tokens))
        )
        parameter = (
            pyparsing.Suppress(cls.keyword(keywords.application)) + name
            if keywords.application is not None
            else pyparsing.NoMatch()
        )
        target = reference + pyparsing.Opt(parameter, default=None)
        definition = (
            pyparsing.Suppress(cls.keyword(keywords.definition))
            + target
            + pyparsing.Suppress(cls.keyword(keywords.equal_to))
            + expression
        ).set_parse_action(
            lambda tokens: Definition(
                target=tokens[0], parameter=tokens[1], value=tokens[2]
            )
        )
        statements = [definition]
        if keywords.rule is not None:
            statements.append(
                (
                    pyparsing.Suppress(cls.keyword(keywords.rule))
                    + reference
                    + pyparsing.Suppress(cls.keyword(keywords.fulfilled))
                ).set_parse_action(lambda tokens: FulfilledRule(target=tokens[0]))
            )
        statements.append(
            (
                pyparsing.Suppress(cls.keyword(keywords.assertion))
                + expression
                + pyparsing.Opt(pyparsing.Suppress("=") + expression, default=None)
            ).set_parse_action(
                lambda tokens: Assertion(expression=tokens[0], expected=tokens[1])
            )
        )
        body = (
            pyparsing.Suppress(cls.keyword(keywords.scope))
            + name
            + pyparsing.Suppress(":")
            + pyparsing.Group(pyparsing.ZeroOrMore(pyparsing.MatchFirst(statements)))
        ).set_parse_action(
            lambda tokens: ScopeBody(name=tokens[0], statements=tokens[1].as_list())
        )
        grammar = pyparsing.ZeroOrMore(body)
        grammar.ignore(pyparsing.Regex(r"#.*"))
        return grammar
