// Query: AddAddedTimestamps
(Table1 as table, Table2 as table, PkColumnName as text, TimestampColumnName as text) as table =>
let
    // Validate if the primary key column exists in both tables
    #"Is PK Valid" = Table.HasColumns(Table1, {PkColumnName}) and Table.HasColumns(Table2, {PkColumnName}),

    // Ensure PK column is treated as text
    #"Current Table" = if #"Is PK Valid" then Table.TransformColumnTypes(Table1, {{PkColumnName, type text}}) else Table1,
    #"Previous Table" = if #"Is PK Valid" then Table.TransformColumnTypes(Table2, {{PkColumnName, type text}}) else Table2,

    // Check if timestamp column exists in the previous table
    #"Newly Timestamped" = not Table.HasColumns(Table2, {TimestampColumnName}),

    // Remove timestamp column from the current table if it exists
    #"Cleared Current Timestamps" = try Table.RemoveColumns(#"Current Table", {TimestampColumnName}) otherwise #"Current Table",

    // Add timestamp column if it's a new timestamped table
    #"Added New Timestamp" = if #"Newly Timestamped" 
        then Table.AddColumn(#"Current Table", TimestampColumnName, each Date.From(DateTime.LocalNow()), type date) 
        else null,

    // Merge previous timestamps if applicable
    #"Merged Previous Timestamps" = if not #"Newly Timestamped" and #"Is PK Valid" 
        then Table.NestedJoin(#"Cleared Current Timestamps", {PkColumnName}, #"Previous Table", {PkColumnName}, "PreviousTable", JoinKind.LeftOuter) 
        else null,

    // Expand timestamp column from previous table
    #"Expanded Previous Timestamps" = if not #"Newly Timestamped" and #"Is PK Valid" 
        then Table.ExpandTableColumn(#"Merged Previous Timestamps", "PreviousTable", {TimestampColumnName}, {TimestampColumnName}) 
        else null,

    // Fill missing timestamps with the current date
    #"Filled In New Timestamps" = if not #"Newly Timestamped" and #"Is PK Valid" 
        then Table.ReplaceValue(#"Expanded Previous Timestamps", null, Date.From(DateTime.LocalNow()), Replacer.ReplaceValue, {TimestampColumnName}) 
        else null,

    // Final table result
    #"Final Result" = if #"Filled In New Timestamps" <> null then #"Filled In New Timestamps" else #"Added New Timestamp",

    #"Ensure Timestamp Type" = Table.TransformColumnTypes(#"Final Result", {{TimestampColumnName, type date}})
in
    #"Ensure Timestamp Type"