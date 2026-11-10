"""
Tests of reading the terms :file:`ground_case.pl` prints.
"""

from __future__ import annotations

from law_as_code_benchmarks.sara.prolog_term import (
    CompoundTerm,
    PrologText,
    TermKey,
    TermReader,
)

# %% reading terms


def test_atoms_numbers_and_unbound_variables_are_kept() -> None:
    """
    Atoms, numbers and unbound variables read back as themselves.
    """
    assert TermReader().read(["alice", 2017, None]) == ["alice", 2017, None]


def test_a_string_is_told_from_the_atom_spelled_the_same() -> None:
    """
    A Prolog string reads back as text, unequal to the atom spelled the same.
    """
    assert TermReader().read({TermKey.TEXT: "usa"}) == PrologText("usa")
    assert TermReader().read({TermKey.TEXT: "usa"}) != "usa"


def test_a_compound_term_reads_its_arguments() -> None:
    """
    A compound term reads back with its functor and arguments.
    """
    term = {
        TermKey.FUNCTOR: "start_",
        TermKey.ARGUMENTS: ["alice_employed", {TermKey.TEXT: "2017-03-15"}],
    }
    assert TermReader().read(term) == CompoundTerm(
        functor="start_", arguments=("alice_employed", PrologText("2017-03-15"))
    )
