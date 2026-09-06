// Query: TableFournisseursCuve
let
    Source = ImportFromIndex("FRM11", "TableFournTank"),
    #"Split Column by Delimiter" = Table.SplitColumn(Source, "NUMÉRO DE CUVE", Splitter.SplitTextByEachDelimiter({"-"}, QuoteStyle.Csv, false), {"NUMÉRO DE CUVE", "To Delete"}),
    #"Changed Type" = Table.TransformColumnTypes(#"Split Column by Delimiter",{{"NUMÉRO DE CUVE", type text}, {"To Delete", type text}}),
    #"Removed Duplicates" = Table.Distinct(#"Changed Type", {"NUMÉRO DE CUVE"})
in
    #"Removed Duplicates"