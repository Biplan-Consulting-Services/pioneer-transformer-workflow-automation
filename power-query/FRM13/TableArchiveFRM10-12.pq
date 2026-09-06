// Query: TableArchiveFRM10-12
let
    Source = ImportFromIndex("Archive active", "TableArchiveFRM10_12"),
    #"Filter Rows" = Table.SelectRows(Source, each ([Order] <> null and [Order] <> "" and [Order] <> "OS")),
    #"Split Column by Delimiter" = Table.SplitColumn(#"Filter Rows", "Order", Splitter.SplitTextByEachDelimiter({"-"}, QuoteStyle.Csv, false), {"Order", "To Delete"}),
    #"Removed Columns" = Table.RemoveColumns(#"Split Column by Delimiter",{"To Delete"}),
    #"Removed Errors" = Table.RemoveRowsWithErrors(#"Removed Columns", {"Order"}),
    #"Grouped Rows" = Table.Group(#"Removed Errors", {"Order"}, {{"Location", each List.Min([Location]), type text}})
in
    #"Grouped Rows"