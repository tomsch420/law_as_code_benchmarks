"""
The Prolog terms SARA's cases are written in, and the reader of their text.

An atom is a :class:`str`, a number an :class:`int` or :class:`float`, an anonymous
variable ``None`` and a list a :class:`list`; strings, named variables and compound
terms have classes of their own, as Prolog tells a string from the atom spelled the same.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from functools import cache

import pyparsing
from typing_extensions import TypeAlias

# %% terms


@dataclass(frozen=True)
class PrologText:
    """A Prolog string, which Prolog never takes for the atom spelled the same."""

    value: str
    """The string's characters."""


@dataclass(frozen=True)
class PrologVariable:
    """A named variable, which every goal of its clause naming it shares."""

    name: str
    """The variable's name, such as ``Start_relationship``."""


@dataclass(frozen=True)
class CompoundTerm:
    """A compound term, such as a fact, a goal or an operator applied to its operands."""

    functor: str
    """The name of the term, such as ``agent_`` or ``,``."""

    arguments: tuple[Term, ...]
    """The arguments, in order."""


Term: TypeAlias = (
    str | int | float | PrologText | PrologVariable | CompoundTerm | list | None
)
"""A Prolog term; ``None`` stands for an anonymous variable and a list holds terms."""


@dataclass(frozen=True)
class Clause:
    """A clause of a case: a fact, or a rule with its body."""

    head: CompoundTerm
    """What the clause states."""

    body: Term = None
    """The goal the head holds under; None for a fact."""


@dataclass(frozen=True)
class Directive:
    """A directive, ``:- Goal.``, which Prolog runs as it loads the file."""

    goal: Term
    """The goal it runs; None for a directive among a case's facts, which is never read."""


# %% reading text


class Operator(StrEnum):
    """The operators SARA's cases write terms with."""

    CLAUSE = ":-"
    """Separates a rule's head from its body, and opens a directive."""

    DISJUNCTION = ";"
    """Either goal holds."""

    IF_THEN = "->"
    """The second goal, where the first holds."""

    CONJUNCTION = ","
    """Both goals hold."""

    NEGATION = "\\+"
    """The goal has no solution."""

    IDENTICAL = "=="
    """Both terms are the same."""

    UNIFICATION = "="
    """Both terms are made the same."""

    DIVISION = "/"
    """Names a predicate by its arity, as in ``s63/3``."""

    DISCONTIGUOUS = "discontiguous"
    """Declares that a predicate's clauses are spread over the file."""

    END = "."
    """Ends a clause."""


class BuiltinPredicate(StrEnum):
    """The predicates of SWI-Prolog and of SARA's utilities that cases call."""

    BETWEEN = "between"
    """``between(Low, High, Number)``: each whole number from *Low* to *High*."""

    MEMBER = "member"
    """``member(Element, List)``: each element of *List*."""

    ATOM_CONCATENATION = "atom_concat"
    """``atom_concat(Left, Right, Atom)``: the atom spelling *Left* then *Right*."""

    FIRST_DAY_OF_YEAR = "first_day_year"
    """``first_day_year(Year, Day)``: January 1 of *Year*, as ``YYYY-MM-DD``."""

    LAST_DAY_OF_YEAR = "last_day_year"
    """``last_day_year(Year, Day)``: December 31 of *Year*, as ``YYYY-MM-DD``."""

    STRING_SPLIT = "split_string"
    """``split_string(Text, Separators, Padding, Parts)``: *Text* split at *Separators*."""

    ATOM_NUMBER = "atom_number"
    """``atom_number(Text, Number)``: the number *Text* spells."""

    BOUND = "nonvar"
    """``nonvar(Term)``: *Term* is bound."""

    UNBOUND = "var"
    """``var(Term)``: *Term* is unbound."""

    DAY_ORDER = "is_before"
    """``is_before(Day, Other)``: *Day* is not after *Other*."""


@dataclass
class PrologReader:
    """
    Reads the Prolog text SARA's cases are written in: clauses, directives, and the terms
    they hold, with the operators of :class:`Operator`.
    """

    def read_clauses(self, text: str) -> list[Clause | Directive]:
        """
        :param text: Clauses and directives, each ending in a full stop.
        :return: The clauses and directives, in order.
        """
        return list(self.clauses_grammar().parse_string(text, parse_all=True))

    def read_term(self, text: str) -> Term:
        """
        :param text: One term, without a full stop.
        :return: The term.
        """
        return self.goal_grammar().parse_string(text, parse_all=True)[0]

    @classmethod
    @cache
    def goal_grammar(cls) -> pyparsing.ParserElement:
        """The grammar of one term, operators included."""
        pyparsing.ParserElement.enable_packrat()
        goal = pyparsing.Forward()
        argument = pyparsing.Forward()
        number = pyparsing.Regex(r"-?\d+(\.\d+)?").set_parse_action(
            lambda tokens: float(tokens[0]) if "." in tokens[0] else int(tokens[0])
        )
        string = pyparsing.QuotedString('"', esc_char="\\").set_parse_action(
            lambda tokens: PrologText(tokens[0])
        )
        quoted_atom = pyparsing.QuotedString("'", esc_char="\\")
        atom = pyparsing.Regex(r"[a-z][A-Za-z0-9_]*") | quoted_atom
        variable = pyparsing.Regex(r"[A-Z_][A-Za-z0-9_]*").set_parse_action(
            lambda tokens: [None if tokens[0] == "_" else PrologVariable(tokens[0])]
        )
        arguments = pyparsing.DelimitedList(argument)
        compound = (
            atom
            + pyparsing.Suppress("(")
            + pyparsing.Group(arguments)
            + pyparsing.Suppress(")")
        ).set_parse_action(
            lambda tokens: CompoundTerm(
                functor=tokens[0], arguments=tuple(tokens[1].as_list())
            )
        )
        prolog_list = (
            pyparsing.Suppress("[")
            + pyparsing.Group(pyparsing.Opt(arguments))
            + pyparsing.Suppress("]")
        ).set_parse_action(lambda tokens: [tokens[0].as_list()])
        primary = (
            number
            | string
            | compound
            | atom
            | variable
            | prolog_list
            | pyparsing.Suppress("(") + goal + pyparsing.Suppress(")")
        )
        comparisons = [
            (
                pyparsing.Literal(Operator.DIVISION),
                2,
                pyparsing.OpAssoc.LEFT,
                cls.fold_operands,
            ),
            (
                pyparsing.Literal(Operator.IDENTICAL)
                | pyparsing.Literal(Operator.UNIFICATION),
                2,
                pyparsing.OpAssoc.LEFT,
                cls.fold_operands,
            ),
        ]
        argument <<= pyparsing.infix_notation(primary, comparisons)
        goal <<= pyparsing.infix_notation(
            primary,
            comparisons
            + [
                (
                    pyparsing.Keyword(Operator.DISCONTIGUOUS),
                    1,
                    pyparsing.OpAssoc.RIGHT,
                    cls.fold_operands,
                ),
                (
                    pyparsing.Literal(Operator.NEGATION),
                    1,
                    pyparsing.OpAssoc.RIGHT,
                    cls.fold_operands,
                ),
                (
                    pyparsing.Literal(Operator.CONJUNCTION),
                    2,
                    pyparsing.OpAssoc.RIGHT,
                    cls.fold_operands,
                ),
                (
                    pyparsing.Literal(Operator.IF_THEN),
                    2,
                    pyparsing.OpAssoc.RIGHT,
                    cls.fold_operands,
                ),
                (
                    pyparsing.Literal(Operator.DISJUNCTION),
                    2,
                    pyparsing.OpAssoc.RIGHT,
                    cls.fold_operands,
                ),
            ],
        )
        return goal

    @classmethod
    @cache
    def clauses_grammar(cls) -> pyparsing.ParserElement:
        """The grammar of a sequence of clauses and directives, comments left out."""
        end = pyparsing.Suppress(pyparsing.Regex(r"\.(?=\s|$)"))
        directive = (
            pyparsing.Suppress(Operator.CLAUSE) + cls.goal_grammar() + end
        ).set_parse_action(lambda tokens: Directive(goal=tokens[0]))
        clause = (
            cls.goal_grammar()
            + pyparsing.Opt(pyparsing.Suppress(Operator.CLAUSE) + cls.goal_grammar())
            + end
        ).set_parse_action(
            lambda tokens: Clause(
                head=tokens[0], body=tokens[1] if len(tokens) > 1 else None
            )
        )
        grammar = pyparsing.ZeroOrMore(directive | clause)
        grammar.ignore(pyparsing.Regex(r"%.*"))
        return grammar

    @staticmethod
    def fold_operands(tokens: pyparsing.ParseResults) -> CompoundTerm:
        """
        :param tokens: One operator application, as :func:`pyparsing.infix_notation`
            groups it: a prefix operator and its operand, or operands and the operators
            between them.
        :return: The application as compound terms, a right-associative chain folded
            from the right and a left-associative one from the left.
        """
        group = tokens[0].as_list()
        if len(group) == 2:
            return CompoundTerm(functor=group[0], arguments=(group[1],))
        if group[1] in (Operator.DIVISION, Operator.IDENTICAL, Operator.UNIFICATION):
            term = group[0]
            for operator, operand in zip(group[1::2], group[2::2]):
                term = CompoundTerm(functor=operator, arguments=(term, operand))
            return term
        term = group[-1]
        for operator, operand in zip(group[-2::-2], group[-3::-2]):
            term = CompoundTerm(functor=operator, arguments=(operand, term))
        return term
