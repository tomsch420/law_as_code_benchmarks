"""
Reads the test files of Catala's examples, in the subset of Catala their tests are
written in, French, English or Polish: the scopes they define, the values and
assertions of each, and the subscopes a test scope declares.
"""

from __future__ import annotations

import calendar
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

from law_as_code_benchmarks.catala.exceptions import (
    AmbiguousAnniversary,
    DurationInDays,
    UnmappedExpression,
)
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

    scope_result: str | None
    """Opens a call of a scope, as ``result of Scope with { … }``; None where no test file of the language uses it."""

    scope_arguments: str | None
    """Opens the arguments of a call of a scope; None where no test file of the language uses it."""

    pattern: str | None
    """Tests which constructor an enumeration's value is of; None where no test file of the language uses it."""

    year: str | None
    """The unit of a duration in years; None where no test file of the language uses it."""

    month: str | None
    """The unit of a duration in months; None where no test file of the language uses it."""

    day: str | None
    """The unit of a duration in days; None where no test file of the language uses it."""

    map_each: str | None
    """Opens a list mapped element by element, as ``map each x among list to expression``; None where no test file of the language uses it."""

    map_among: str | None
    """Names the list mapped; None where no test file of the language uses it."""

    map_to: str | None
    """Names what each element is mapped to; None where no test file of the language uses it."""

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
        scope_result="résultat",
        scope_arguments="avec",
        pattern="sous forme",
        year="an",
        month="mois",
        day="jour",
        map_each="transforme chaque",
        map_among="parmi",
        map_to="en",
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
        scope_result=None,
        scope_arguments=None,
        pattern=None,
        year=None,
        month=None,
        day=None,
        map_each=None,
        map_among=None,
        map_to=None,
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
        scope_result=None,
        scope_arguments=None,
        pattern=None,
        year=None,
        month=None,
        day=None,
        map_each=None,
        map_among=None,
        map_to=None,
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
class ScopeCall:
    """A scope called with its inputs, as ``result of Scope with { -- input: value }``."""

    scope: Reference
    """The scope called."""

    arguments: dict[str, CatalaValue]
    """The value of each input, by name."""


@dataclass(frozen=True)
class FieldAccess:
    """A field of a structure, or an output of a scope called, as ``(expression).field``."""

    value: CatalaValue
    """The structure, or the scope called."""

    field_name: str
    """The field."""


@dataclass(frozen=True)
class ListMap:
    """Each element of a list mapped to an expression of it, as ``map each element among list to expression``."""

    element: str
    """The name standing for each element in the expression."""

    elements: CatalaValue
    """The list."""

    expression: CatalaValue
    """The expression each element is mapped to."""

    def scope_calls(self) -> list[ScopeCall]:
        """
        :return: The scope call the expression makes for each element, the element in
            place of every argument naming it.
        :raises UnmappedExpression: Where the expression is no scope call, nor a field of one.
        """
        call = self.expression
        if isinstance(call, FieldAccess):
            call = call.value
        if not isinstance(call, ScopeCall):
            raise UnmappedExpression(expression=self.expression)
        return [
            ScopeCall(
                scope=call.scope,
                arguments={
                    name: element
                    if argument == Reference(parts=(self.element,))
                    else argument
                    for name, argument in call.arguments.items()
                },
            )
            for element in self.elements
        ]


@dataclass(frozen=True)
class Duration:
    """A duration in years, months and days, which Catala keeps apart."""

    years: int = 0
    """The whole years."""

    months: int = 0
    """The whole months."""

    days: int = 0
    """The whole days."""

    @property
    def whole_months(self) -> int:
        """
        The duration in months, a year counting twelve.

        :raises DurationInDays: Where the duration has days.
        """
        if self.days:
            raise DurationInDays(days=self.days)
        return 12 * self.years + self.months

    def date_after(self, day: datetime.date) -> datetime.date:
        """
        :return: The day the duration after *day*: its years and months first, keeping
            the day of the month, then its days.
        :raises AmbiguousAnniversary: Where the years and months land on a day the month
            lacks, a day Catala refuses to round.
        """
        months = 12 * day.year + day.month - 1 + 12 * self.years + self.months
        year, month = divmod(months, 12)
        if day.day > calendar.monthrange(year, month + 1)[1]:
            raise AmbiguousAnniversary(day=day, duration=self)
        return day.replace(year=year, month=month + 1) + datetime.timedelta(
            days=self.days
        )


@dataclass(frozen=True)
class ConstructorPattern:
    """That a value is of an enumeration's constructor, whatever its content, as ``value with pattern Constructor``."""

    constructor: Reference
    """The constructor."""

    def is_matched_by(self, value: CatalaValue) -> bool:
        """:return: Whether *value* is of the constructor, bare or with content."""
        match value:
            case ConstructorWithContent():
                return value.constructor.last_part == self.constructor.last_part
            case Reference():
                return value.last_part == self.constructor.last_part
        return False


@dataclass(frozen=True)
class Application:
    """A function applied to an argument, as ``function of argument``."""

    function: Reference
    """The function."""

    argument: CatalaValue
    """The argument, or a tuple of the arguments of a function of several."""


@dataclass(frozen=True)
class Negation:
    """An expression negated, as ``not expression``."""

    operand: CatalaValue
    """The expression negated."""


CatalaValue: TypeAlias = (
    Money
    | Fraction
    | Duration
    | datetime.date
    | int
    | bool
    | Reference
    | StructureLiteral
    | ConstructorWithContent
    | ScopeCall
    | Application
    | Negation
    | FieldAccess
    | ListMap
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
    """``assertion expression``, ``assertion expression = expected`` or ``assertion expression with pattern Constructor``."""

    expression: CatalaValue
    """The expression asserted."""

    expected: CatalaValue | ConstructorPattern | None = None
    """The value it is asserted to equal or the constructor it is asserted to be of; None where the expression is asserted to hold."""

    def asserted_value(self) -> tuple[CatalaValue, CatalaValue | ConstructorPattern]:
        """:return: The expression asserted, any negation removed, and what it is asserted to be: ``expected``, or whether it holds."""
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

    constants: list[Definition] = field(default_factory=list)
    """The values declared outside any scope, as ``declaration name content Type equals value``."""

    stated_results: dict[str, dict[str, str]] = field(default_factory=dict)
    """
    The results Catala's command line prints for each test scope, by variable, as the
    file's ``catala-test-cli`` blocks state them and Catala's own tests check them.
    """

    language: CatalaLanguage | None = None
    """The language the file is written in; None for a program not read from a file."""

    def stated_result(self, scope: str, variable: str) -> CatalaValue:
        """:return: The value the command line prints for *variable* of the test scope *scope*."""
        return CatalaTestReader.expression_grammar(self.language).parse_string(
            self.stated_results[scope][variable], parse_all=True
        )[0]

    @property
    def test_scopes(self) -> list[ScopeBody]:
        """The test scopes, in order."""
        return [scope for scope in self.scopes if scope.is_test]

    @property
    def data_definitions(self) -> dict[str, Definition]:
        """The definitions of the scopes that are no test and the constants, by the name of the variable defined."""
        definitions = {
            statement.target.last_part: statement
            for scope in self.scopes
            if not scope.is_test
            for statement in scope.statements
            if isinstance(statement, Definition)
        }
        return definitions | {
            constant.target.last_part: constant for constant in self.constants
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
            case ScopeCall():
                return ScopeCall(
                    scope=value.scope,
                    arguments={
                        name: self.resolve(argument)
                        for name, argument in value.arguments.items()
                    },
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
        :return: The scopes and constants its Catala code blocks define, declarations
            of scopes read only for which scopes are tests and which subscopes each
            declares.
        """
        code = "\n".join(
            re.findall(r"```catala(?:-metadata)?\n(.*?)```", text, flags=re.DOTALL)
        )
        keywords = self.language.value
        declarations = re.findall(
            rf"^(#\[test\]\s*)?{re.escape(keywords.declaration)}\s+"
            rf"{re.escape(keywords.scope)}\s+(\w+)\s*:\s*\n((?:[ \t]+\S.*\n?|\n(?=[ \t]+\S))*)",
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
            rf"^(#\[test\]\s*)?{re.escape(keywords.declaration)}\s+"
            rf"{re.escape(keywords.scope)}\b.*\n(?:[ \t]+\S.*\n?|\n(?=[ \t]+\S))*",
            "",
            code,
            flags=re.MULTILINE,
        )
        parsed = self.program_grammar(self.language).parse_string(body, parse_all=True)
        stated_results = {
            scope: self.printed_results(printed)
            for scope, printed in re.findall(
                r"```catala-test-cli\n\$ catala test-scope (\w+)[^\n]*\n(.*?)```",
                text,
                flags=re.DOTALL,
            )
        }
        return CatalaProgram(
            stated_results=stated_results,
            language=self.language,
            scopes=[
                ScopeBody(
                    name=name,
                    statements=statements,
                    is_test=name in test_names,
                    subscopes=subscopes.get(name, {}),
                )
                for name, statements in self.merged_statements(parsed).items()
            ],
            constants=[
                constant for constant in parsed if isinstance(constant, Definition)
            ],
        )

    @staticmethod
    def merged_statements(
        parsed: list[ScopeBody | Definition],
    ) -> dict[str, list[Statement]]:
        """:return: The statements of each scope, in order, a scope written in several bodies merged."""
        statements: dict[str, list[Statement]] = {}
        for scope in parsed:
            if isinstance(scope, ScopeBody):
                statements.setdefault(scope.name, []).extend(scope.statements)
        return statements

    @staticmethod
    def printed_results(printed: str) -> dict[str, str]:
        """
        :param printed: The result block Catala's command line prints for a test scope.
        :return: The text of each variable's value, by name, a value spanning the lines
            indented under its own; lines before the first variable left out.
        """
        results: dict[str, list[str]] = {}
        for line in re.findall(r"^│ (.*)$", printed, flags=re.MULTILINE):
            opened = re.match(r"^(\w+) =(.*)$", line)
            if opened:
                results[opened.group(1)] = [opened.group(2)]
            elif results:
                list(results.values())[-1].append(line)
        return {name: " ".join(lines).strip() for name, lines in results.items()}

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
            r"\$\d[\d,]*(\.\d+)?|-?\d[\d ]*(,\d+)?\s*€|\d[\d ]*([.,]\d+)?\s*PLN"
        ).set_parse_action(lambda tokens: cls.money_from_text(tokens[0]))
        date = pyparsing.Regex(r"\|\d{4}-\d{2}-\d{2}\|").set_parse_action(
            lambda tokens: datetime.date.fromisoformat(tokens[0].strip("|"))
        )
        percentage = pyparsing.Regex(r"\d+([.,]\d+)?\s*%").set_parse_action(
            lambda tokens: Fraction(tokens[0].rstrip("% ").replace(",", ".")) / 100
        )
        duration_units = {
            unit: field_name
            for unit, field_name in [
                (keywords.year, "years"),
                (keywords.month, "months"),
                (keywords.day, "days"),
            ]
            if unit is not None
        }
        duration = (
            (
                pyparsing.Regex(r"\d+")
                + pyparsing.MatchFirst([cls.keyword(unit) for unit in duration_units])
            ).set_parse_action(
                lambda tokens: Duration(**{duration_units[tokens[1]]: int(tokens[0])})
            )
            if duration_units
            else pyparsing.NoMatch()
        )
        decimal = pyparsing.Regex(r"-?\d+[.,]\d+").set_parse_action(
            lambda tokens: Fraction(tokens[0].replace(",", "."))
        )
        integer = pyparsing.Regex(
            r"-?\d{1,3}(?: \d{3})+(?![\d,])|-?\d+"
        ).set_parse_action(lambda tokens: int(tokens[0].replace(" ", "")))
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
        field_access = (
            parenthesized + pyparsing.Suppress(".") + name
        ).set_parse_action(
            lambda tokens: FieldAccess(value=tokens[0], field_name=tokens[1])
        )
        primary = (
            money
            | date
            | percentage
            | duration
            | decimal
            | integer
            | boolean
            | catala_list
            | structure
            | field_access
            | parenthesized
        )
        alternatives = []
        if keywords.map_each is not None:
            alternatives.append(
                (
                    pyparsing.Suppress(cls.keyword(keywords.map_each))
                    + name
                    + pyparsing.Suppress(cls.keyword(keywords.map_among))
                    + expression
                    + pyparsing.Suppress(cls.keyword(keywords.map_to))
                    + expression
                ).set_parse_action(
                    lambda tokens: ListMap(
                        element=tokens[0], elements=tokens[1], expression=tokens[2]
                    )
                )
            )
        if keywords.scope_result is not None:
            alternatives.append(
                (
                    pyparsing.Suppress(cls.keyword(keywords.scope_result))
                    + pyparsing.Suppress(cls.keyword(keywords.application))
                    + reference
                    + pyparsing.Suppress(cls.keyword(keywords.scope_arguments))
                    + pyparsing.Suppress("{")
                    + pyparsing.Group(pyparsing.ZeroOrMore(field_value))
                    + pyparsing.Suppress("}")
                ).set_parse_action(
                    lambda tokens: ScopeCall(
                        scope=tokens[0],
                        arguments={
                            argument_name: argument
                            for argument_name, argument in tokens[1]
                        },
                    )
                )
            )
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
                    + pyparsing.DelimitedList(expression, ",")
                ).set_parse_action(
                    lambda tokens: Application(
                        function=tokens[0],
                        argument=tokens[1] if len(tokens) == 2 else tuple(tokens[1:]),
                    )
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
        """The grammar of the scope bodies and constants of a file in *language*, declarations of scopes removed and comments left out."""
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
        expected = pyparsing.Suppress("=") + expression
        if keywords.pattern is not None:
            expected |= (
                pyparsing.Suppress(cls.keyword(keywords.pattern)) + reference
            ).set_parse_action(lambda tokens: ConstructorPattern(constructor=tokens[0]))
        statements.append(
            (
                pyparsing.Suppress(cls.keyword(keywords.assertion))
                + expression
                + pyparsing.Opt(expected, default=None)
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
        constant = (
            (
                pyparsing.Suppress(cls.keyword(keywords.declaration))
                + reference
                + pyparsing.Suppress(cls.keyword(keywords.content))
                + pyparsing.Suppress(reference)
                + pyparsing.Suppress(cls.keyword(keywords.equal_to))
                + expression
            ).set_parse_action(
                lambda tokens: Definition(target=tokens[0], value=tokens[1])
            )
            if keywords.content is not None
            else pyparsing.NoMatch()
        )
        grammar = pyparsing.ZeroOrMore(body | constant)
        grammar.ignore(pyparsing.Regex(r"#.*"))
        return grammar
