"""
The arithmetic OpenFisca's YAML tests write some values in, such as ``1412.64 / 12``,
evaluated exactly.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from functools import cache

import pyparsing
from typing_extensions import Callable

# %% operators


class ArithmeticOperator(StrEnum):
    """
    The operators of an arithmetic expression, each spelled as written.
    """

    PLUS = "+"
    """
    Addition, or a sign.
    """

    MINUS = "-"
    """
    Subtraction, or negation.
    """

    TIMES = "*"
    """
    Multiplication.
    """

    DIVIDED_BY = "/"
    """
    Division.
    """

    @property
    def function(self) -> Callable[[Fraction, Fraction], Fraction]:
        """
        The binary function the operator stands for.
        """
        match self:
            case ArithmeticOperator.PLUS:
                return operator.add
            case ArithmeticOperator.MINUS:
                return operator.sub
            case ArithmeticOperator.TIMES:
                return operator.mul
            case ArithmeticOperator.DIVIDED_BY:
                return operator.truediv


# %% reading


@dataclass(frozen=True)
class ArithmeticReader:
    """
    Reads a number, or an expression of numbers with ``+``, ``-``, ``*``, ``/`` and
    parentheses, as the exact fraction it evaluates to.
    """

    def read(self, text: str | int | float) -> Fraction:
        """
        :param text: The expression; a number YAML already read is taken as written.
        :return: Its exact value.
        """
        return self.grammar().parse_string(str(text), parse_all=True)[0]

    @classmethod
    @cache
    def grammar(cls) -> pyparsing.ParserElement:
        """
        The grammar of an expression, evaluating it as it is parsed.
        """
        number = pyparsing.Regex(r"\d+(\.\d*)?|\.\d+").set_parse_action(
            lambda tokens: Fraction(tokens[0])
        )
        return pyparsing.infix_notation(
            number,
            [
                (
                    pyparsing.one_of("+ -"),
                    1,
                    pyparsing.OpAssoc.RIGHT,
                    lambda tokens: cls.signed(*tokens[0]),
                ),
                (
                    pyparsing.one_of("* /"),
                    2,
                    pyparsing.OpAssoc.LEFT,
                    lambda tokens: cls.folded(*tokens[0]),
                ),
                (
                    pyparsing.one_of("+ -"),
                    2,
                    pyparsing.OpAssoc.LEFT,
                    lambda tokens: cls.folded(*tokens[0]),
                ),
            ],
        )

    @staticmethod
    def signed(sign: str, value: Fraction) -> Fraction:
        """:return: *value* with *sign* in front of it."""
        return -value if sign == ArithmeticOperator.MINUS else value

    @staticmethod
    def folded(first: Fraction, *rest: Fraction | str) -> Fraction:
        """:return: *first* combined from left to right with the operators and operands of *rest*."""
        value = first
        for symbol, operand in zip(rest[::2], rest[1::2]):
            value = ArithmeticOperator(symbol).function(value, operand)
        return value
