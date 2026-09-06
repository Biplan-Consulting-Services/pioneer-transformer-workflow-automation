// Query: Query2
let
    Source = ArchivedOrders,
    #"Filtered Rows" = Table.SelectRows(Source, each [#"PO Item #"] <> null and [#"PO Item #"] <> ""),
    #"Grouped Rows" = Table.Group(#"Filtered Rows", {"PO Item #"}, {{"Orders", each List.Max([Order]), type text}, {"Client", each List.Max([Client]), type text}, {"Order Date", each List.Max([Order Date]), type nullable date}})
in
    #"Grouped Rows"