// Query: TableLocales
let
    Source = Excel.CurrentWorkbook(){[Name="TableLocales"]}[Content],
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"Standard name", type text}, {"Original", type text}, {"FR", type text}, {"EN", type text}, {"Calculated", type logical}})
in
    #"Changed Type"