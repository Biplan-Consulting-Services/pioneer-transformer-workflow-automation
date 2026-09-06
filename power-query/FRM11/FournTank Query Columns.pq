// Query: FournTank Query Columns
let
    Source = TableLocales,
    #"Filtered Rows" = Table.SelectRows(Source, each ([Calculated] = false)),
    #"Standard name" = #"Filtered Rows"[Standard name]
in
    #"Standard name"