"""
Conditions on the text of a term, for the rules that read a name, such as an employer's
whose name begins with *state of*.

Prolog reads the text of an atom and of a string alike here, as ``atom_prefix/2`` and
``sub_atom/5`` do.
"""

from __future__ import annotations

from dataclasses import dataclass

from krrood.entity_query_language.predicate import Predicate
from krrood.entity_query_language.verbalization.vocabulary.english import Prepositions
from krrood.entity_query_language.verbalization.vocabulary.parts_of_speech import (
    Noun,
    Verb,
    clause,
)
from typing_extensions import Any

from law_as_code_benchmarks.sara.prolog_term import PrologText, Term

# %% text of a term


@dataclass(eq=False)
class TextCondition(Predicate):
    """
    A condition on the text of an atom or a string; any other term fails it.
    """

    term: Term
    """
    The term whose text is read.
    """

    text: str
    """
    The text it is compared with.
    """

    def term_text(self) -> str | None:
        """:return: The characters of :attr:`term`; None if it is neither an atom nor a string."""
        if isinstance(self.term, PrologText):
            return self.term.value
        if isinstance(self.term, str):
            return self.term
        return None


@dataclass(eq=False)
class BeginsWith(TextCondition):
    """
    Whether the text of a term begins with :attr:`text`.
    """

    def __call__(self) -> bool:
        term_text = self.term_text()
        return term_text is not None and term_text.startswith(self.text)

    @classmethod
    def _verbalization_fragment_(cls, fields: Any) -> Any:
        return clause(
            Noun(fields["term"]), Verb("begin"), Prepositions.WITH, Noun(fields["text"])
        )


@dataclass(eq=False)
class EndsWith(TextCondition):
    """
    Whether the text of a term ends with :attr:`text`.
    """

    def __call__(self) -> bool:
        term_text = self.term_text()
        return term_text is not None and term_text.endswith(self.text)

    @classmethod
    def _verbalization_fragment_(cls, fields: Any) -> Any:
        return clause(
            Noun(fields["term"]), Verb("end"), Prepositions.WITH, Noun(fields["text"])
        )
