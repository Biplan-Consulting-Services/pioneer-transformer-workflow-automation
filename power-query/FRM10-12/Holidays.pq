// Query: Holidays
let
    Source = Excel.CurrentWorkbook(){[Name="TableFeries"]}[Content],
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"Fériés", type date}})
in
    #"Changed Type"