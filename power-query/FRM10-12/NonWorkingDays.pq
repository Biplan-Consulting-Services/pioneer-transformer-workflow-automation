// Query: NonWorkingDays
let
    Source = Vacations,
    #"Added Column DateList" = Table.AddColumn(Source, "DateList", each List.Dates([Début], Duration.Days([Fin] - [Début]) + 1, #duration(1, 0, 0, 0))),
    #"Combined Column DateList" = List.Combine(#"Added Column DateList"[DateList]),
    #"Combined With Feries" = List.Combine({#"Combined Column DateList", Holidays[#"Fériés"]})
in
    #"Combined With Feries"