// Query: TableSuppliers
let
    Source = Excel.CurrentWorkbook(){[Name="TableSuppliers"]}[Content],
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"Supplier", type text}, {"Supplies Tank", type logical}, {"Supplies Paint", type logical}, {"Table Name", type text}, {"Indexed Report Name", type text}})
in
    #"Changed Type"