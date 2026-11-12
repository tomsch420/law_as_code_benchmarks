% Expands one SARA case into the ground facts it states and the goal it tests, as JSON.
%
% Usage, from SARA's root directory: swipl ground_case.pl -- <case file>
% Prints {"facts": [...], "tests": [...]}: a fact for every solution of every clause the
% case defines, and each test directive's goal. Atoms are JSON strings, Prolog strings
% are {"text": ...}, compound terms are {"functor": ..., "arguments": [...]}, a named
% variable of a test goal is {"variable": ...} and any other unbound variable is null.
% The test goals are not run.

:- use_module(library(lists)).
:- use_module(library(apply)).
:- use_module(library(readutil)).
:- use_module(library(http/json)).
:- initialization(main, main).

main :-
    current_prolog_flag(argv, [CaseFile]),
    read_file_to_string(CaseFile, Text, []),
    sub_string(Text, Before, _, _, "\n% Test"),
    sub_string(Text, 0, Before, _, FactsText),
    sub_string(Text, Before, _, 0, TestsText),
    terminated(FactsText, TerminatedFactsText),
    terms(TerminatedFactsText, FactTerms),
    named_terms(TestsText, TestTerms),
    foldl(load_case_term, FactTerms, [], ReversedClauses),
    reverse(ReversedClauses, Clauses),
    include(test_directive, TestTerms, TestDirectives),
    maplist(directive_goal, TestDirectives, Tests),
    ground_facts(Clauses, Facts),
    maplist(term_json, Facts, FactsJson),
    maplist(term_json, Tests, TestsJson),
    json_write_dict(current_output, _{facts: FactsJson, tests: TestsJson}, [width(0)]),
    nl.

% terminated(+Text, -Terminated): Text, ending in a full stop. A few cases leave the full
% stop off their last fact, which would otherwise swallow the test directive.
terminated(Text, Terminated) :-
    split_string(Text, "", " \t\n", [Stripped]),
    (   sub_string(Stripped, _, 1, 0, ".")
    ->  Terminated = Stripped
    ;   string_concat(Stripped, ".\n", Terminated)
    ).

% terms(+Text, -Terms): the terms Text holds, in order.
terms(Text, Terms) :-
    setup_call_cleanup(open_string(Text, Stream), read_terms(Stream, Terms), close(Stream)).

% named_terms(+Text, -Terms): the terms Text holds, each named variable replaced by
% '$variable'(Name), so that conjuncts sharing a variable can be told apart.
named_terms(Text, Terms) :-
    setup_call_cleanup(open_string(Text, Stream), read_named_terms(Stream, Terms), close(Stream)).

read_named_terms(Stream, Terms) :-
    read_term(Stream, Term, [variable_names(Names)]),
    (   Term == end_of_file
    ->  Terms = []
    ;   maplist(name_variable, Names),
        Terms = [Term|More],
        read_named_terms(Stream, More)
    ).

name_variable(Name = '$variable'(Name)).

read_terms(Stream, Terms) :-
    read_term(Stream, Term, []),
    (   Term == end_of_file
    ->  Terms = []
    ;   Terms = [Term|More],
        read_terms(Stream, More)
    ).

% load_case_term(+Term, +Clauses, -MoreClauses): loads what a directive among the facts
% asks for and collects each clause as a Head-Body pair. In place of the statutes, only
% their utilities are loaded, for the dates the case's clauses compute. A clause of a
% predicate the utilities do not define is asserted, so that the case's other clauses
% can call it.
load_case_term((:- [_]), Clauses, Clauses) :- !,
    load_files(['statutes/prolog/utils'], [silent(true)]).
load_case_term((:- _), Clauses, Clauses) :- !.
load_case_term((Head :- Body), Clauses, [Head-Body|Clauses]) :- !,
    assert_unless_utility(Head, Body).
load_case_term(Head, Clauses, [Head-true|Clauses]) :-
    assert_unless_utility(Head, true).

assert_unless_utility(Head, _) :-
    functor(Head, Name, Arity),
    functor(Template, Name, Arity),
    predicate_property(Template, defined),
    \+ predicate_property(Template, dynamic),
    !.
assert_unless_utility(Head, Body) :-
    functor(Head, Name, Arity),
    dynamic(Name/Arity),
    assertz((Head :- Body)).

test_directive((:- halt)) :- !, fail.
test_directive((:- _)).

directive_goal((:- Goal), Goal).

% ground_facts(+Clauses, -Facts): every solution of every clause. A clause that needs its
% arguments bound, as one computing an event's role from the event's name does, is solved
% once for every name the case's other facts give as a first argument: in its first
% argument, or, where that is not enough, in its first two.
ground_facts(Clauses, Facts) :-
    partition(enumerable, Clauses, Enumerable, NeedingNames),
    findall(Fact, (member(Head-Body, Enumerable), solution(Head, Body, Fact)), FirstFacts),
    findall(Name, (member(Fact, FirstFacts), arg(1, Fact, Name)), Names),
    list_to_set(Names, NameSet),
    findall(
        Fact,
        (member(Head-Body, NeedingNames), named_solution(Head, Body, NameSet, Fact)),
        NamedFacts
    ),
    append(FirstFacts, NamedFacts, AllFacts),
    list_to_set(AllFacts, Facts).

enumerable(Head-Body) :-
    catch(forall(solution(Head, Body, _), true), error(instantiation_error, _), fail).

solution(Head, Body, Fact) :-
    copy_term(Head-Body, Fact-Goal),
    call(Goal).

named_solution(Head, Body, Names, Fact) :-
    copy_term(Head-Body, Template-_),
    arg(1, Template, First),
    (   var(First), enumerable_once_named(Head-Body, Names)
    ->  member(Name, Names),
        copy_term(Head-Body, Fact-Goal),
        arg(1, Fact, Name),
        call(Goal)
    ;   member(Name, Names),
        member(Other, Names),
        copy_term(Head-Body, Fact-Goal),
        arg(1, Fact, Name),
        arg(2, Fact, Other),
        call(Goal)
    ).

enumerable_once_named(Head-Body, Names) :-
    catch(
        forall((member(Name, Names), copy_term(Head-Body, Fact-Goal), arg(1, Fact, Name)), forall(call(Goal), true)),
        error(instantiation_error, _),
        fail
    ).

% term_json(+Term, -Json): Term in the JSON form the header describes.
term_json(Term, null) :- var(Term), !.
term_json('$variable'(Name), _{variable: Name}) :- !.
term_json(Term, Term) :- number(Term), !.
term_json(Term, _{text: Term}) :- string(Term), !.
term_json([], []) :- !.
term_json(Term, Name) :- atom(Term), !, atom_string(Term, Name).
term_json(Term, Json) :- is_list(Term), !, maplist(term_json, Term, Json).
term_json(Term, _{functor: Name, arguments: Json}) :-
    compound_name_arguments(Term, Name, Arguments),
    maplist(term_json, Arguments, Json).
