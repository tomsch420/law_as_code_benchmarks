"""
The rules SARA's cases state facts with, each kind an object that expands into its
facts: most facts are stated one by one, but some rules state a series of events at
once, such as Bob's upkeep of his house every year from 2004 to 2019, Alice's 87
employees in 2015, or farm work on twelve listed days.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from functools import cached_property

from krrood.ormatic.utils import classproperty
from typing_extensions import Self, TypeAlias

from law_as_code_benchmarks.sara.exceptions import UnrecognizedCaseRule
from law_as_code_benchmarks.sara.prolog_term import (
    BuiltinPredicate,
    Clause,
    CompoundTerm,
    Operator,
    PrologText,
    PrologVariable,
    Term,
)

# %% bindings of a clause's variables

Bindings: TypeAlias = dict[str, Term]
"""
The values a clause's variables take in one of its solutions, by variable name.
"""


def instantiated(term: Term, bindings: Bindings) -> Term:
    """
    :param term: A term of a clause.
    :param bindings: Values of the clause's variables.
    :return: *term* with each variable replaced by its value, None where it has none.
    """
    if isinstance(term, PrologVariable):
        return bindings.get(term.name)
    if isinstance(term, list):
        return [instantiated(element, bindings) for element in term]
    if isinstance(term, CompoundTerm):
        return CompoundTerm(
            functor=term.functor,
            arguments=tuple(
                instantiated(argument, bindings) for argument in term.arguments
            ),
        )
    return term


def spelling(term: Term) -> str | None:
    """:return: The characters of an atom, a string or a number; None for any other term."""
    if isinstance(term, PrologText):
        return term.value
    if isinstance(term, (str, int, float)):
        return str(term)
    return None


def conjuncts(goal: Term) -> list[Term]:
    """:return: The goals of a conjunction, in order; a single goal for any other goal."""
    if isinstance(goal, CompoundTerm) and goal.functor == Operator.CONJUNCTION:
        return conjuncts(goal.arguments[0]) + conjuncts(goal.arguments[1])
    return [goal]


def is_call(goal: Term, functor: str, arity: int) -> bool:
    """:return: Whether *goal* calls the predicate *functor*/*arity*."""
    return (
        isinstance(goal, CompoundTerm)
        and goal.functor == functor
        and len(goal.arguments) == arity
    )


def hashable(term: Term) -> object:
    """:return: *term*, its lists turned into tuples, so that equal terms hash equally."""
    if isinstance(term, list):
        return tuple(hashable(element) for element in term)
    if isinstance(term, CompoundTerm):
        return (term.functor, tuple(hashable(argument) for argument in term.arguments))
    return term


# %% parts of series of events


@dataclass
class EventName:
    """
    An event's name spelled from a fixed beginning and one value, as
    ``bob_maintains_household_2004``.
    """

    beginning: Term
    """
    What the name begins with.
    """

    ending: Term
    """
    What follows: a constant, or a variable bound before the name is spelled.
    """

    variable: str
    """
    The variable the name is bound to.
    """

    @classmethod
    def from_goal(cls, goal: Term) -> Self | None:
        """:return: The name ``atom_concat(Beginning, Ending, Name)`` spells; None for any other goal."""
        if not is_call(goal, BuiltinPredicate.ATOM_CONCATENATION, 3):
            return None
        beginning, ending, name = goal.arguments
        if not isinstance(name, PrologVariable):
            return None
        return cls(beginning=beginning, ending=ending, variable=name.name)

    def bind(self, bindings: Bindings) -> None:
        """
        Binds :attr:`variable` to the name spelled under *bindings*.
        """
        bindings[self.variable] = spelling(
            instantiated(self.beginning, bindings)
        ) + spelling(instantiated(self.ending, bindings))


class YearBoundary(StrEnum):
    """
    The days of a year a rule takes a period from.
    """

    FIRST = BuiltinPredicate.FIRST_DAY_OF_YEAR
    """
    January 1.
    """

    LAST = BuiltinPredicate.LAST_DAY_OF_YEAR
    """
    December 31.
    """

    def day(self, year: int) -> PrologText:
        """:return: This day of *year*, as SARA's utilities spell it."""
        month_and_day = "01-01" if self is YearBoundary.FIRST else "12-31"
        return PrologText(f"{year}-{month_and_day}")


@dataclass
class DayOfYear:
    """
    A day bound for each year of a series: its first or last day, or, in one year, a day
    the case states, as ``(Year == 2017 -> Start = "2017-09-16" ; first_day_year(Year, Start))``.
    """

    year_variable: str
    """
    The variable holding the year.
    """

    variable: str
    """
    The variable the day is bound to.
    """

    boundary: YearBoundary
    """
    The day of every other year.
    """

    exceptional_year: int | None = None
    """
    The one year the case states another day for.
    """

    exceptional_day: PrologText | None = None
    """
    The day stated for :attr:`exceptional_year`.
    """

    @classmethod
    def from_goal(cls, goal: Term) -> Self | None:
        """:return: The day *goal* binds; None for a goal of another shape."""
        boundary = next(
            (boundary for boundary in YearBoundary if is_call(goal, boundary, 2)), None
        )
        if boundary is not None:
            year, day = goal.arguments
            if isinstance(year, PrologVariable) and isinstance(day, PrologVariable):
                return cls(
                    year_variable=year.name, variable=day.name, boundary=boundary
                )
            return None
        if not is_call(goal, Operator.DISJUNCTION, 2):
            return None
        exception, otherwise = goal.arguments
        usual = cls.from_goal(otherwise)
        if usual is None or not is_call(exception, Operator.IF_THEN, 2):
            return None
        condition, consequence = exception.arguments
        if not (
            is_call(condition, Operator.IDENTICAL, 2)
            and is_call(consequence, Operator.UNIFICATION, 2)
            and condition.arguments[0] == PrologVariable(usual.year_variable)
            and consequence.arguments[0] == PrologVariable(usual.variable)
        ):
            return None
        usual.exceptional_year = condition.arguments[1]
        usual.exceptional_day = consequence.arguments[1]
        return usual

    def bind(self, bindings: Bindings) -> None:
        """
        Binds :attr:`variable` to the day of the year :attr:`year_variable` holds.
        """
        year = bindings[self.year_variable]
        bindings[self.variable] = (
            self.exceptional_day
            if year == self.exceptional_year
            else self.boundary.day(year)
        )


# %% kinds of rules


@dataclass
class CaseRule(ABC):
    """
    A clause of a case, expanded into the facts it states.
    """

    clause: Clause
    """
    The clause.
    """

    @classmethod
    @abstractmethod
    def from_clause(cls, clause: Clause, expansion: FactExpansion) -> Self | None:
        """:return: The rule *clause* states, if it has this kind's shape; otherwise None."""

    @abstractmethod
    def solutions(self, expansion: FactExpansion) -> list[Bindings]:
        """:return: The values of the clause's variables in each of its solutions, in Prolog's order."""

    @classproperty
    def is_about_named_events(cls) -> bool:
        """
        Whether the rule states facts about events other rules name, and so is expanded
        after them.
        """
        return False

    def facts(self, expansion: FactExpansion) -> list[CompoundTerm]:
        """:return: The facts the rule states, one for each solution."""
        return [
            instantiated(self.clause.head, bindings)
            for bindings in self.solutions(expansion)
        ]


@dataclass
class StatedFact(CaseRule):
    """
    A fact the case states as it is.
    """

    @classmethod
    def from_clause(cls, clause: Clause, expansion: FactExpansion) -> Self | None:
        return cls(clause=clause) if clause.body is None else None

    def solutions(self, expansion: FactExpansion) -> list[Bindings]:
        return [{}]


@dataclass
class SeriesOfEvents(CaseRule):
    """
    Events or facts, one for each whole number of a span or each member of a list: each
    year Bob maintains his house, each of Alice's 87 employees, or each person she
    employs.
    """

    index_variable: str
    """
    The variable holding the year, number or member.
    """

    indices: list[Term]
    """
    The years, numbers or members, in order.
    """

    names: list[EventName] = field(default_factory=list)
    """
    The names spelled for each index, in order.
    """

    days: list[DayOfYear] = field(default_factory=list)
    """
    The days bound for each index, which is then a year.
    """

    @classmethod
    def from_clause(cls, clause: Clause, expansion: FactExpansion) -> Self | None:
        if clause.body is None:
            return None
        enumeration, *steps = conjuncts(clause.body)
        series = cls.from_enumeration(clause, enumeration)
        if series is None:
            return None
        for step in steps:
            name = EventName.from_goal(step)
            day = DayOfYear.from_goal(step)
            if name is not None:
                series.names.append(name)
            elif day is not None:
                series.days.append(day)
            else:
                return None
        return series

    @classmethod
    def from_enumeration(cls, clause: Clause, goal: Term) -> Self | None:
        """:return: The series *goal* enumerates the indices of, without names or days; None for another goal."""
        if is_call(goal, BuiltinPredicate.BETWEEN, 3):
            low, high, index = goal.arguments
            indices = list(range(low, high + 1))
        elif is_call(goal, BuiltinPredicate.MEMBER, 2):
            index, indices = goal.arguments
        else:
            return None
        if not isinstance(index, PrologVariable) or not isinstance(indices, list):
            return None
        return cls(clause=clause, index_variable=index.name, indices=indices)

    def solutions(self, expansion: FactExpansion) -> list[Bindings]:
        solutions = []
        for index in self.indices:
            bindings = {self.index_variable: index}
            for name in self.names:
                name.bind(bindings)
            for day in self.days:
                day.bind(bindings)
            solutions.append(bindings)
        return solutions


@dataclass
class FactOnDaysOfPeriod(CaseRule):
    """
    A fact holding on each day of a period, and, asked with the day left open, at all,
    as ``(nonvar(Day), is_before("2017-06-01", Day), is_before(Day, "2017-08-31")) ;
    var(Day)``.

    Expanded, it is stated once, with the day left open.
    """

    day_variable: str
    """
    The variable holding the day.
    """

    start: Term
    """
    The period's first day.
    """

    end: Term
    """
    The period's last day.
    """

    @classmethod
    def from_clause(cls, clause: Clause, expansion: FactExpansion) -> Self | None:
        if not is_call(clause.body, Operator.DISJUNCTION, 2):
            return None
        within_period, left_open = clause.body.arguments
        goals = conjuncts(within_period)
        if len(goals) != 3 or not is_call(left_open, BuiltinPredicate.UNBOUND, 1):
            return None
        bound, after_start, before_end = goals
        day = left_open.arguments[0]
        if not (
            isinstance(day, PrologVariable)
            and is_call(bound, BuiltinPredicate.BOUND, 1)
            and bound.arguments[0] == day
            and is_call(after_start, BuiltinPredicate.DAY_ORDER, 2)
            and after_start.arguments[1] == day
            and is_call(before_end, BuiltinPredicate.DAY_ORDER, 2)
            and before_end.arguments[0] == day
        ):
            return None
        return cls(
            clause=clause,
            day_variable=day.name,
            start=after_start.arguments[0],
            end=before_end.arguments[1],
        )

    def solutions(self, expansion: FactExpansion) -> list[Bindings]:
        return [{}]


@dataclass
class RosterDay:
    """
    One day of a roster, and who works on it.
    """

    day: PrologText
    """
    The day.
    """

    worker_variable: str
    """
    The variable holding the person working.
    """

    workers: list[Term]
    """
    Who works, in the order the case lists them.
    """

    @classmethod
    def from_goal(cls, goal: Term, day_variable: PrologVariable) -> Self | None:
        """:return: The day ``(Day == D, member(Worker, Workers))`` states; None for a goal of another shape."""
        if not is_call(goal, Operator.CONJUNCTION, 2):
            return None
        condition, membership = goal.arguments
        if not (
            is_call(condition, Operator.IDENTICAL, 2)
            and condition.arguments[0] == day_variable
            and is_call(membership, BuiltinPredicate.MEMBER, 2)
            and isinstance(membership.arguments[0], PrologVariable)
        ):
            return None
        worker, workers = membership.arguments
        return cls(
            day=condition.arguments[1], worker_variable=worker.name, workers=workers
        )


@dataclass
class RosterOfEvents(CaseRule):
    """
    One event for each person working on each listed day, named after the day and the
    person, as ``alice_employer_2017-01-24_bob``.
    """

    day_variable: str
    """
    The variable holding the day.
    """

    roster: list[RosterDay]
    """
    The days, in order, and who works on each.
    """

    names: list[EventName]
    """
    The names spelled for each day and person, in order; the last names the event.
    """

    @classmethod
    def from_clause(cls, clause: Clause, expansion: FactExpansion) -> Self | None:
        if clause.body is None:
            return None
        goals = conjuncts(clause.body)
        if len(goals) < 3 or not is_call(goals[0], BuiltinPredicate.MEMBER, 2):
            return None
        listed_days, roster, *steps = goals
        day_variable, days = listed_days.arguments
        roster_days = [
            RosterDay.from_goal(alternative, day_variable)
            for alternative in cls.alternatives(roster)
        ]
        names = [EventName.from_goal(step) for step in steps]
        if None in roster_days or None in names:
            return None
        roster_by_day = {roster_day.day: roster_day for roster_day in roster_days}
        if not isinstance(days, list) or not set(days) <= roster_by_day.keys():
            return None
        return cls(
            clause=clause,
            day_variable=day_variable.name,
            roster=[roster_by_day[day] for day in days],
            names=names,
        )

    @classmethod
    def alternatives(cls, goal: Term) -> list[Term]:
        """:return: The goals of a disjunction, in order; a single goal for any other goal."""
        if is_call(goal, Operator.DISJUNCTION, 2):
            return cls.alternatives(goal.arguments[0]) + cls.alternatives(
                goal.arguments[1]
            )
        return [goal]

    def solutions(self, expansion: FactExpansion) -> list[Bindings]:
        solutions = []
        for roster_day in self.roster:
            for worker in roster_day.workers:
                bindings = {
                    self.day_variable: roster_day.day,
                    roster_day.worker_variable: worker,
                }
                for name in self.names:
                    name.bind(bindings)
                solutions.append(bindings)
        return solutions


@dataclass
class FactsAboutSeries(CaseRule):
    """
    A fact for each event of a series another rule of the case states, as
    ``payment_(Event) :- bob_household_maintenance(_, Event, _, _)``, with further names
    spelled from the event's, as ``atom_concat(Service, "_payment", Payment)``.
    """

    series: CompoundTerm
    """
    The call of the predicate stating the series.
    """

    names: list[EventName] = field(default_factory=list)
    """
    The names spelled for each event, in order.
    """

    @classmethod
    def from_clause(cls, clause: Clause, expansion: FactExpansion) -> Self | None:
        if clause.body is None:
            return None
        series, *steps = conjuncts(clause.body)
        if not isinstance(series, CompoundTerm) or not expansion.defines(series):
            return None
        names = [EventName.from_goal(step) for step in steps]
        if None in names:
            return None
        return cls(clause=clause, series=series, names=names)

    def solutions(self, expansion: FactExpansion) -> list[Bindings]:
        solutions = []
        for fact in expansion.facts_of(self.series):
            bindings = self.matching_bindings(fact)
            if bindings is None:
                continue
            for name in self.names:
                name.bind(bindings)
            solutions.append(bindings)
        return solutions

    def matching_bindings(self, fact: CompoundTerm) -> Bindings | None:
        """:return: The values :attr:`series` binds matching *fact*; None if it does not match."""
        bindings = {}
        for pattern, value in zip(self.series.arguments, fact.arguments):
            if pattern is None:
                continue
            if not isinstance(pattern, PrologVariable):
                if pattern != value:
                    return None
            elif bindings.setdefault(pattern.name, value) != value:
                return None
        return bindings


@dataclass
class NamePart:
    """
    One part of an event's name, split at a separator, and the characters it must be.
    """

    variable: str | None
    """
    The variable the part is bound to; None for a part left anonymous.
    """

    required: str | None = None
    """
    The characters the part must be; None for any.
    """

    @classmethod
    def from_term(cls, term: Term) -> Self:
        """:return: The part *term* stands for in a list of parts."""
        return cls(variable=term.name if isinstance(term, PrologVariable) else None)


@dataclass
class EventNamePattern:
    """
    The parts an event's name must split into, as ``split_string(Event, "_", "", [X, Y,
    Z])``.
    """

    variable: str
    """
    The variable holding the event's name.
    """

    separator: str
    """
    The characters the name is split at.
    """

    parts: list[NamePart]
    """
    The parts, in order.
    """

    @classmethod
    def from_goal(cls, goal: Term) -> Self | None:
        """:return: The pattern a ``split_string`` goal splits a name into; None for any other goal."""
        if not is_call(goal, BuiltinPredicate.STRING_SPLIT, 4):
            return None
        name, separator, _, parts = goal.arguments
        if not isinstance(name, PrologVariable) or not isinstance(parts, list):
            return None
        return cls(
            variable=name.name,
            separator=spelling(separator),
            parts=[NamePart.from_term(part) for part in parts],
        )

    def bind(self, name: Term, bindings: Bindings) -> bool:
        """
        Binds :attr:`variable` to *name* and the parts' variables to its parts.

        :return: Whether *name* splits into parts matching the pattern.
        """
        characters = spelling(name)
        if characters is None:
            return False
        pieces = characters.split(self.separator)
        if len(pieces) != len(self.parts):
            return False
        for part, piece in zip(self.parts, pieces):
            if part.required is not None and piece != part.required:
                return False
            if part.variable is not None:
                bindings[part.variable] = PrologText(piece)
        bindings[self.variable] = name
        return True


@dataclass
class SharedPart:
    """
    Two parts, of two names, that must be the same, as ``Yp == Ys``.
    """

    variable: str
    """
    One part's variable.
    """

    other_variable: str
    """
    The other part's variable.
    """


@dataclass
class NumberedPart:
    """
    A part spelling a whole number in a span, as ``atom_number(Z, Id), between(1, 87,
    Id)``.
    """

    part_variable: str
    """
    The part's variable.
    """

    number_variable: str
    """
    The variable the number is bound to.
    """

    low: int | None = None
    """
    The span's lowest number; None until the span is read.
    """

    high: int | None = None
    """
    The span's highest number; None until the span is read.
    """

    def bind(self, bindings: Bindings) -> bool:
        """
        Binds :attr:`number_variable` to the number the part spells.

        :return: Whether the part spells a number within the span.
        """
        characters = bindings[self.part_variable].value
        if not characters.isdigit():
            return False
        bindings[self.number_variable] = int(characters)
        return self.low <= bindings[self.number_variable] <= self.high


@dataclass
class FactsAboutNamedEvents(CaseRule):
    """
    A fact for each event, among those the case's other facts name, whose name splits into
    parts of a pattern: ``agent_(Service, Employee)`` for every ``workforalice_2015_N``,
    with ``Employee`` spelled ``employee_2015_N``.
    """

    patterns: list[EventNamePattern] = field(default_factory=list)
    """
    The patterns, one for each of the head's leading arguments, in order.
    """

    shared_parts: list[SharedPart] = field(default_factory=list)
    """
    The parts two names must agree in.
    """

    numbered_parts: list[NumberedPart] = field(default_factory=list)
    """
    The parts spelling a number in a span.
    """

    names: list[EventName] = field(default_factory=list)
    """
    The names spelled from the parts, in order.
    """

    @classproperty
    def is_about_named_events(cls) -> bool:
        """
        True, unlike :meth:`CaseRule.is_about_named_events`.
        """
        return True

    @classmethod
    def from_clause(cls, clause: Clause, expansion: FactExpansion) -> Self | None:
        if clause.body is None:
            return None
        rule = cls(clause=clause)
        if not all(rule.add_goal(goal) for goal in conjuncts(clause.body)):
            return None
        pattern_variables = [
            PrologVariable(pattern.variable) for pattern in rule.patterns
        ]
        leading_arguments = list(clause.head.arguments[: len(pattern_variables)])
        if not pattern_variables or leading_arguments != pattern_variables:
            return None
        return rule

    def add_goal(self, goal: Term) -> bool:
        """
        Adds what *goal* requires of the names to this rule.

        :return: Whether *goal* is of a shape this kind of rule has.
        """
        pattern = EventNamePattern.from_goal(goal)
        name = EventName.from_goal(goal)
        if pattern is not None:
            self.patterns.append(pattern)
        elif name is not None:
            self.names.append(name)
        elif is_call(goal, Operator.IDENTICAL, 2):
            return self.add_identity(*goal.arguments)
        elif is_call(goal, BuiltinPredicate.ATOM_NUMBER, 2):
            part, number = goal.arguments
            self.numbered_parts.append(
                NumberedPart(part_variable=part.name, number_variable=number.name)
            )
        elif is_call(goal, BuiltinPredicate.BETWEEN, 3):
            low, high, number = goal.arguments
            numbered_part = next(
                part
                for part in self.numbered_parts
                if PrologVariable(part.number_variable) == number
            )
            numbered_part.low, numbered_part.high = low, high
        else:
            return False
        return True

    def add_identity(self, part: Term, other: Term) -> bool:
        """
        Adds that the part *part* stands for is *other*: a string, or another part.

        :return: Whether *part* is a part of a pattern of this rule.
        """
        parts = {
            part.variable: part
            for pattern in self.patterns
            for part in pattern.parts
            if part.variable is not None
        }
        if not isinstance(part, PrologVariable) or part.name not in parts:
            return False
        if isinstance(other, PrologText):
            parts[part.name].required = other.value
        else:
            self.shared_parts.append(
                SharedPart(variable=part.name, other_variable=other.name)
            )
        return True

    def solutions(self, expansion: FactExpansion) -> list[Bindings]:
        solutions = [{}]
        for pattern in self.patterns:
            extended_solutions = []
            for bindings in solutions:
                for name in expansion.event_names:
                    extended = dict(bindings)
                    if pattern.bind(name, extended):
                        extended_solutions.append(extended)
            solutions = extended_solutions
        return [
            bindings for bindings in solutions if self.bind_spelled_values(bindings)
        ]

    def bind_spelled_values(self, bindings: Bindings) -> bool:
        """
        Binds the numbers and the names the parts spell.

        :return: Whether the parts agree where they must and spell numbers in their
            spans.
        """
        if any(
            bindings[shared.variable] != bindings[shared.other_variable]
            for shared in self.shared_parts
        ):
            return False
        if not all(numbered.bind(bindings) for numbered in self.numbered_parts):
            return False
        for name in self.names:
            name.bind(bindings)
        return True


# %% a case's facts


@dataclass
class FactExpansion:
    """
    The facts a case's clauses state, its rules expanded.
    """

    clauses: list[Clause]
    """
    The case's clauses, in order.
    """

    rule_kinds: list[type[CaseRule]] = field(
        default_factory=lambda: [
            StatedFact,
            SeriesOfEvents,
            FactOnDaysOfPeriod,
            RosterOfEvents,
            FactsAboutSeries,
            FactsAboutNamedEvents,
        ]
    )
    """
    The kinds of rules a clause is recognized as, tried in order.
    """

    @cached_property
    def rules(self) -> list[CaseRule]:
        """
        The rule each clause states, in order.

        :raises UnrecognizedCaseRule: For a clause of no kind in :attr:`rule_kinds`.
        """
        rules = []
        for clause in self.clauses:
            rule = next(
                (
                    rule
                    for kind in self.rule_kinds
                    if (rule := kind.from_clause(clause, self)) is not None
                ),
                None,
            )
            if rule is None:
                raise UnrecognizedCaseRule(clause=clause)
            rules.append(rule)
        return rules

    def defines(self, goal: CompoundTerm) -> bool:
        """:return: Whether a clause of the case states facts of the predicate *goal* calls."""
        return any(
            is_call(clause.head, goal.functor, len(goal.arguments))
            for clause in self.clauses
        )

    def facts_of(self, goal: CompoundTerm) -> list[CompoundTerm]:
        """:return: The facts the case's rules state of the predicate *goal* calls, in order."""
        return [
            fact
            for rule in self.rules
            if is_call(rule.clause.head, goal.functor, len(goal.arguments))
            for fact in rule.facts(self)
        ]

    @cached_property
    def facts_naming_events(self) -> list[CompoundTerm]:
        """
        The facts of the rules not about named events, in order.
        """
        return [
            fact
            for rule in self.rules
            if not rule.is_about_named_events
            for fact in rule.facts(self)
        ]

    @cached_property
    def event_names(self) -> list[Term]:
        """
        The first arguments of :attr:`facts_naming_events`, each once, in order.
        """
        return list(
            {
                hashable(fact.arguments[0]): fact.arguments[0]
                for fact in self.facts_naming_events
                if fact.arguments
            }.values()
        )

    @cached_property
    def facts(self) -> list[CompoundTerm]:
        """
        Every fact the case states, each once, in order: its rules' about named events
        last.
        """
        named = [
            fact
            for rule in self.rules
            if rule.is_about_named_events
            for fact in rule.facts(self)
        ]
        return list(
            {hashable(fact): fact for fact in self.facts_naming_events + named}.values()
        )
