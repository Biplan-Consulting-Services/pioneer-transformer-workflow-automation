// Query: DefaultPromisedDate
let
    Source = ProductionStepLeadDays,
    DaysToAdd = Source{0}[#"Assignation par défaut pour livraison (jours)"],
    Today = Date.From(DateTime.LocalNow()),
    #"Result Date" = Date.AddDays(Today, DaysToAdd)
in
    #"Result Date"