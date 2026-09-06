// Query: FournTank Self-Ref Columns
let
    Source = TableLocales,
    #"Filtered Rows" = Table.SelectRows(Source, each ([Imported From Suppliers] = false) and ([Imported From Pioneer] = false) and ([Calculated] = false)),
    #"Standard name" = #"Filtered Rows"[Standard name]
in
    #"Standard name"