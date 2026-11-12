"""
Tests of reading the Prolog text SARA's cases are written in.
"""

from __future__ import annotations

from pathlib import Path

from law_as_code_benchmarks.sara.prolog_term import (
    BuiltinPredicate,
    Clause,
    CompoundTerm,
    Directive,
    Operator,
    PrologReader,
    PrologText,
    PrologVariable,
)

# %% the clauses of a file


def statements() -> list[Clause | Directive]:
    """:return: The clauses and directives of :file:`case_files/terms.pl`."""
    return PrologReader().read_clauses(
        (Path(__file__).parent / "case_files" / "terms.pl").read_text()
    )


def test_comments_are_left_out_and_directives_told_from_clauses() -> None:
    """
    A comment is not read, and a directive is read as a directive, not a clause.
    """
    directive, *clauses = statements()
    assert directive == Directive(
        goal=CompoundTerm(
            functor=Operator.DISCONTIGUOUS,
            arguments=(CompoundTerm(functor=Operator.DIVISION, arguments=("s63", 3)),),
        )
    )
    assert all(isinstance(clause, Clause) for clause in clauses)


# %% terms


def test_a_string_is_told_from_the_atom_spelled_the_same() -> None:
    """
    A Prolog string reads as text, unequal to the atom spelled the same.
    """
    assert statements()[1].head.arguments == ("usa", PrologText("usa"))


def test_numbers_lists_and_quoted_atoms_are_read() -> None:
    """
    Whole and decimal numbers, lists and quoted atoms read as Python values.
    """
    assert statements()[2].head.arguments == ("alice", [1, 2.5], "quoted atom")


def test_an_anonymous_variable_is_none_and_a_named_one_keeps_its_name() -> None:
    """
    ``_`` reads as None, and a named variable as a variable of that name.
    """
    clause = statements()[3]
    assert clause.head.arguments == (None, PrologVariable("Day"))
    assert clause.body == CompoundTerm(
        functor=BuiltinPredicate.FIRST_DAY_OF_YEAR,
        arguments=(2017, PrologVariable("Day")),
    )


# %% operators


def test_a_conjunction_binds_tighter_than_a_disjunction() -> None:
    """
    ``a ; b, c`` reads as ``a ; (b, c)``.
    """
    variable = PrologVariable("X")
    assert statements()[4].body == CompoundTerm(
        functor=Operator.DISJUNCTION,
        arguments=(
            CompoundTerm(functor="a", arguments=(variable,)),
            CompoundTerm(
                functor=Operator.CONJUNCTION,
                arguments=(
                    CompoundTerm(functor="b", arguments=(variable,)),
                    CompoundTerm(functor="c", arguments=(variable,)),
                ),
            ),
        ),
    )


def test_a_negation_applies_to_the_whole_comparison() -> None:
    """
    ``\\+ X == y`` reads as ``\\+ (X == y)``.
    """
    assert statements()[5].body == CompoundTerm(
        functor=Operator.NEGATION,
        arguments=(
            CompoundTerm(
                functor=Operator.IDENTICAL, arguments=(PrologVariable("X"), "y")
            ),
        ),
    )


def test_a_term_is_read_on_its_own() -> None:
    """
    A single term, without a full stop, reads as that term.
    """
    assert PrologReader().read_term('agent_(alice_dies, "x")') == CompoundTerm(
        functor="agent_", arguments=("alice_dies", PrologText("x"))
    )
