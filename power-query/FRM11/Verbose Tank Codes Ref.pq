// Query: Verbose Tank Codes Ref
let
    Source = Table.Combine({
        Table.SelectColumns(TableCuveCodes, {"Statut", "Code"}),
        Table.SelectColumns(TablePeintureCodes, {"Statut", "Code"}),
        Table.SelectColumns(TablePioneerCodes, {"Statut", "Code"})},
    {"Statut", "Code"}
    ),
    #"Removed Duplicates" = Table.Distinct(Source, {"Code"})
in
    #"Removed Duplicates"