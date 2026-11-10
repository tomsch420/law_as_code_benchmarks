% Times SARA's Prolog program answering one case's test goal.
%
% Usage, from SARA's root directory: swipl answer_case.pl -- <case file>
% Loads the case as SARA's program does, statutes included, but runs its test directive only
% afterwards, timed. Prints {"passed": true|false|null, "seconds": ...}: whether the test
% directive succeeded, which is whether the program gives the case's reference answer, and
% the wall-clock time of the directive alone. "passed" is null where the case holds no test.

:- initialization(main, main).
:- dynamic test_goal/1.

user:term_expansion((:- halt), []).
user:term_expansion((:- Goal), []) :-
    Goal \= [_|_],
    Goal \= discontiguous(_),
    assertz(test_goal(Goal)).

main :-
    current_prolog_flag(argv, [CaseFile]),
    load_files(CaseFile, [silent(true)]),
    (   test_goal(Goal)
    ->  get_time(Start),
        (   catch(Goal, _, fail) -> Passed = true ; Passed = false ),
        get_time(End),
        Seconds is End - Start,
        format('{"passed": ~w, "seconds": ~15f}~n', [Passed, Seconds])
    ;   format('{"passed": null, "seconds": null}~n', [])
    ).
