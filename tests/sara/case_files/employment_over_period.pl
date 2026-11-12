s3306_c(alice_employer,alice,bob,Day,_) :-
    (
        nonvar(Day),
        is_before("2017-06-01",Day),
        is_before(Day,"2017-08-31")
    );
    var(Day).
