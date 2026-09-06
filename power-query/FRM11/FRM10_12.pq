// Query: FRM10_12
let
    Source = ImportFromIndex("FRM10-12", "TableOrders"),
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"Order", type text}})
in
    #"Changed Type"