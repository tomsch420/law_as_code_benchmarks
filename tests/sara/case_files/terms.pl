% A comment, which is not read.
:- discontiguous s63/3.
country_(usa,"usa").
amounts_(alice,[1,2.5],'quoted atom').
start_(_,Day) :- first_day_year(2017,Day).
choice_(X) :- (a(X) ; b(X), c(X)).
exception_(X) :- \+ X == y.
