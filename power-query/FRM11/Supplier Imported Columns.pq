// Query: Supplier Imported Columns
let
    Source = TableLocales,
    #"Filtered Rows" = Table.SelectRows(Source, each ([Imported From Suppliers] = true)),
    #"Standard name" = #"Filtered Rows"[Standard name]
in
    #"Standard name"