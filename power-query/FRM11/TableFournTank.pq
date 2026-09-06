// Query: TableFournTank
let
    Source = Excel.CurrentWorkbook(){[Name="TableFournTank"]}[Content],
    ColumnsList = Table.ColumnNames(Source),
    // List of {column name, null} pairs to allow error replacing
    ColumnsNullList = List.Transform(ColumnsList, each {_, null}),
    #"Replaced Errors" = Table.ReplaceErrorValues(Source, ColumnsNullList),
    #"Changed Type" = Table.TransformColumnTypes(#"Replaced Errors",{{"NUMÉRO DE CUVE", type text}}),
    #"Filtered Rows" = Table.SelectRows(#"Changed Type", each ([NUMÉRO DE CUVE] <> null))
in
    #"Filtered Rows"