service_(Service_event) :- between(1,2,Employee_id),
    atom_concat("workforalice_2015_",Employee_id,Service_event).
payment_(Payment_event) :- between(1,2,Employee_id),
    atom_concat('payment_2015_',Employee_id,Payment_event).
agent_(Service_event,Employee) :- split_string(Service_event,"_","",[X,Y,Z]),
    X=="workforalice", Y=="2015",
    atom_concat('employee_2015_',Z,Employee).
purpose_(Payment_event,Service_event) :- split_string(Payment_event,"_","",[Xp,Yp,Zp]),
    split_string(Service_event,"_","",[Xs,Ys,Zs]),
    Xp=="payment",Xs=="workforalice",Yp==Ys,Zp==Zs.
