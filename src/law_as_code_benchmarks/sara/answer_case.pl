% Times SARA's Prolog program answering one case's test goal.
%
% Usage, from SARA's root directory: swipl answer_case.pl -- <case file>
% Loads the case as SARA's program does, statutes included, but runs its test directive only
% afterwards, timed. Prints {"passed": true|false|null, "seconds": ...}: whether the test
% directive succeeded, which is whether the program gives the case's reference answer, and
% the wall-clock time of the directive alone. "passed" is null where the case holds no test.

:- initialization(main, main).
:- dynamic test_goal/1.
:- dynamic case_file/1.

% Only the case file's own directives are held back; those of the statutes and of the
% libraries they autoload, module headers included, run as loaded.
user:term_expansion((:- halt), []) :-
    loading_case_file.
user:term_expansion((:- Goal), []) :-
    loading_case_file,
    Goal \= [_|_],
    Goal \= discontiguous(_),
    assertz(test_goal(Goal)).

loading_case_file :-
    prolog_load_context(source, Source),
    case_file(Source).

main :-
    current_prolog_flag(argv, [CaseFile]),
    absolute_file_name(CaseFile, AbsoluteCaseFile),
    assertz(case_file(AbsoluteCaseFile)),
    load_files(AbsoluteCaseFile, [silent(true)]),
    (   test_goal(Goal)
    ->  get_time(Start),
        (   catch(Goal, _, fail) -> Passed = true ; Passed = false ),
        get_time(End),
        Seconds is End - Start,
        format('{"passed": ~w, "seconds": ~15f}~n', [Passed, Seconds])
    ;   format('{"passed": null, "seconds": null}~n', [])
    ).
