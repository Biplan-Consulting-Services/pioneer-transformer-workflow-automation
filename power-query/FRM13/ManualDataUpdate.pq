// Query: ManualDataUpdate
let
    Source = Excel.CurrentWorkbook(){[Name="TableOrders"]}[Content],
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"Order", type text}})
in
    #"Changed Type"