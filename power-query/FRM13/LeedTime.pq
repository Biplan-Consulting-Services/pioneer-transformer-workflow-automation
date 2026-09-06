// Query: LeedTime
let
    Source = Excel.CurrentWorkbook(){[Name="LeedTime"]}[Content],
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"Lead time", Int64.Type}})
in
    #"Changed Type"