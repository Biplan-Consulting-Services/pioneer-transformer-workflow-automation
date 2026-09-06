// Query: Rows to purge
let
    Source = ArchiveFRM11,
    #"Merged Queries" = Table.NestedJoin(Source, {"NUMÉRO DE CUVE"}, ArchiveFRM10_12, {"Order"}, "ArchiveFRM10_12", JoinKind.LeftOuter),
    #"Expanded ArchiveFRM10_12" = Table.ExpandTableColumn(#"Merged Queries", "ArchiveFRM10_12", {"Location", "Status"}, {"Location.1", "Status.1"}),
    #"Added Custom" = Table.AddColumn(#"Expanded ArchiveFRM10_12", "Already Tanked", each List.Contains({"XT", "TE", "FI", "LI"}, [Location.1]) or ([Location.1] = "TA" and Text.Contains([Status.1], "TE"))),
    #"Filtered Rows" = Table.SelectRows(#"Added Custom", each ([Already Tanked] = true)),
    //#"Filtered Rows" = Table.SelectRows(Source, each ([Status] = "Reçu Pioneer")),
    #"Removed Other Columns" = Table.SelectColumns(#"Filtered Rows", {"NUMÉRO DE CUVE"})
in
    #"Removed Other Columns"