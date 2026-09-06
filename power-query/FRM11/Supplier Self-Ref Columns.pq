// Query: Supplier Self-Ref Columns
let
    Source = TableLocales,
    #"Filtered Rows" = Table.SelectRows(Source, each ([Imported From Suppliers] = false) and ([Imported From Pioneer] = false) and ([In Tank Suppliers] = true or [In Paint Suppliers] = true)),
    #"Standard name" = #"Filtered Rows"[Standard name]
in
    #"Standard name"