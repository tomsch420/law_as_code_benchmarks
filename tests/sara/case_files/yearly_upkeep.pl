bob_household_maintenance(Year,Event,Start_day,End_day) :-
    between(2017,2019,Year),
    atom_concat('bob_maintains_household_',Year,Event),
    (((Year==2017)->(Start_day="2017-09-16"));first_day_year(Year,Start_day)),
    last_day_year(Year,End_day).
payment_(Event) :- bob_household_maintenance(_,Event,_,_).
start_(Event,Start_day) :- bob_household_maintenance(_,Event,Start_day,_).
