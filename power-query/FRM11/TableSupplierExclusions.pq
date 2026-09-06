// Query: TableSupplierExclusions
let
    Source = Excel.CurrentWorkbook(){[Name="TableSupplierExclusions"]}[Content],
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"Supplier", type text}, {"Column", type text}})
in
    #"Changed Type"