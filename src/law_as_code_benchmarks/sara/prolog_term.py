"""
The Prolog terms SARA's cases are written in, as :file:`ground_case.pl` prints them.

An atom is a :class:`str`, a number an :class:`int` or :class:`float`, an unbound variable
``None`` and a list a :class:`list`; a Prolog string and a compound term have classes of
their own, since Prolog tells a string from the atom of the same spelling.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from typing_extensions import TypeAlias

# %% terms


@dataclass(frozen=True)
class PrologText:
    """A Prolog string, which Prolog never takes for the atom spelled the same."""

    value: str
    """The string's characters."""


@dataclass(frozen=True)
class CompoundTerm:
    """A compound term, such as a fact or a goal."""

    functor: str
    """The name of the term, such as ``agent_``."""

    arguments: tuple[Term, ...]
    """The arguments, in order."""


Term: TypeAlias = str | int | float | PrologText | CompoundTerm | list | None
"""A Prolog term; ``None`` stands for an unbound variable and a list holds terms."""


# %% reading the JSON form


class TermKey(StrEnum):
    """The keys of the JSON objects :file:`ground_case.pl` writes terms as."""

    TEXT = "text"
    """The characters of a Prolog string."""

    FUNCTOR = "functor"
    """The name of a compound term."""

    ARGUMENTS = "arguments"
    """The arguments of a compound term."""


@dataclass
class TermReader:
    """Reads the terms of :file:`ground_case.pl`'s output back into :data:`Term` values."""

    def read(self, value: Any) -> Term:
        """
        :param value: A term as decoded from the JSON :file:`ground_case.pl` writes.
        :return: The term.
        """
        if isinstance(value, list):
            return [self.read(element) for element in value]
        if not isinstance(value, dict):
            return value
        if TermKey.TEXT in value:
            return PrologText(value[TermKey.TEXT])
        return CompoundTerm(
            functor=value[TermKey.FUNCTOR],
            arguments=tuple(
                self.read(argument) for argument in value[TermKey.ARGUMENTS]
            ),
        )
