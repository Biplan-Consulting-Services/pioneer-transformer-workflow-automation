// Query: FournTank
let
    Source = #"Imported FRM10_12 Data",
    #"Filtered Rows" = Table.SelectRows(Source, each [NUMÉRO DE CUVE] <> null and not Text.Contains([NUMÉRO DE CUVE], "SA") and not Text.Contains([NUMÉRO DE CUVE], "W") and not Text.Contains([NUMÉRO DE CUVE], "R") and not Text.Contains([NUMÉRO DE CUVE], "OS")),
    #"Removed Duplicates" = Table.Distinct(#"Filtered Rows", {"NUMÉRO DE CUVE"}),
    #"Merged Queries" = Table.NestedJoin(#"Removed Duplicates", {"NUMÉRO DE CUVE"}, TableFournTank, {"NUMÉRO DE CUVE"}, "TableFournTank", JoinKind.LeftOuter),
    #"Valid Self-Ref Columns" = List.Intersect({#"FournTank Self-Ref Columns", Table.ColumnNames(TableFournTank)}),
    #"Expanded TableFournTank" = Table.ExpandTableColumn(#"Merged Queries", "TableFournTank", #"Valid Self-Ref Columns", #"Valid Self-Ref Columns"),
    #"Common Columns with Archive" = List.Intersect({Table.ColumnNames(#"Expanded TableFournTank"), Table.ColumnNames(ArchiveFRM11)}),
    #"Merge with Archive" = Table.NestedJoin(#"Expanded TableFournTank", #"Common Columns with Archive", ArchiveFRM11, #"Common Columns with Archive", "ArchiveFRM11", JoinKind.LeftOuter),
    #"Expanded ArchiveFRM11" = Table.ExpandTableColumn(#"Merge with Archive", "ArchiveFRM11", {"NUMÉRO DE CUVE"}, {"NUMÉRO DE CUVE.1"}),
    #"Added Custom" = Table.AddColumn(#"Expanded ArchiveFRM11", "In Archive", each [NUMÉRO DE CUVE.1] <> null, type logical),
    #"Valid Columns" = List.Intersect({#"FournTank Query Columns", Table.ColumnNames(#"Added Custom")}),
    #"Select Columns" = Table.SelectColumns(#"Added Custom", #"Valid Columns"),
    #"Merged Rows to Purge" = Table.NestedJoin(#"Select Columns", {"NUMÉRO DE CUVE"}, #"Rows to purge", {"NUMÉRO DE CUVE"}, "Rows to purge", JoinKind.LeftAnti),
    #"Removed Columns" = Table.RemoveColumns(#"Merged Rows to Purge", {"Rows to purge"}),
    #"Added Timestamps" = AddAddedTimestamps(#"Removed Columns", TableFournTank, "NUMÉRO DE CUVE", "Date Added")
in
    #"Added Timestamps"