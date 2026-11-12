agricultural_service(Event,Employee,Day) :-
    member(Day, ["2017-01-24","2017-02-04"]),
    (
        (
            Day == "2017-01-24",
            member(Employee, [bob,cameron])
        );
        (
            Day == "2017-02-04",
            member(Employee, [dan])
        )
    ),
    atom_concat("alice_employer_",Day,Tmp),
    atom_concat(Tmp,"_",Tmp2),
    atom_concat(Tmp2,Employee,Event).
payment_for_labor(Payment_event,Service_event,Employee,Day) :-
    agricultural_service(Service_event,Employee,Day),
    atom_concat(Service_event,"_payment",Payment_event).
payment_(Event) :- payment_for_labor(Event,_,_,_).
