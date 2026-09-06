// Query: Query1
let 
        RemoteFileIndex = "FRM10-12", 
        RemoteTable = "TableOrders", 
        LocalTable = "TableArchiveFRM10_12", 
        PrimaryKey = "Order",
        UpdateDateColName = "Last Synchronisation Date",
        Today = DateTime.Date(DateTime.LocalNow()),
        Source = ImportFromIndex(RemoteFileIndex, RemoteTable),
        #"Remote Columns" = Table.ColumnNames(Source),
        #"Local Source Exists" = try Excel.CurrentWorkbook(){[Name=LocalTable]}[Content] otherwise null,
        #"Local Source Raw" = if #"Local Source Exists" <> null then #"Local Source Exists" else #table(#"Remote Columns", {}),
        #"Local Source" = if Table.HasColumns(#"Local Source Raw", UpdateDateColName) then #"Local Source Raw" else Table.AddColumn(#"Local Source Raw", UpdateDateColName, each Today, type date),
        #"Local Columns" = Table.ColumnNames(#"Local Source"),
        #"Removed Remote Columns" = List.Difference(#"Local Columns", #"Remote Columns"),
        #"Added Remote Columns" = List.Difference(#"Remote Columns", #"Local Columns"),
        #"Added Removed Columns to Remote" = AddMultipleNullColumns(Source, #"Removed Remote Columns"),
        #"Added New Columns to Local" = AddMultipleNullColumns(#"Local Source", #"Added Remote Columns"),
        #"Columns Order" = List.Combine({#"Remote Columns", #"Removed Remote Columns"}),
        #"Reordered Remote Source" = Table.ReorderColumns(#"Added Removed Columns to Remote", #"Columns Order"),
        #"Reordered Local Source" = Table.ReorderColumns(#"Added New Columns to Local", #"Columns Order"),
        #"Merged Local Source" = Table.NestedJoin(#"Reordered Local Source", {PrimaryKey}, #"Reordered Remote Source", {PrimaryKey}, "TableRemote", JoinKind.LeftAnti),
        #"Removed Columns" = Table.RemoveColumns(#"Merged Local Source", {"TableRemote"}),
        #"Remote Rows with Sync Date" = Table.TransformColumns(#"Reordered Remote Source", {{UpdateDateColName, each Today, type date}}),
        #"Combine Local and Remote" = Table.Combine({#"Removed Columns", #"Remote Rows with Sync Date"}),
        #"Removed Duplicates" = Table.Distinct(#"Combine Local and Remote", PrimaryKey)
in
    #"Removed Duplicates"