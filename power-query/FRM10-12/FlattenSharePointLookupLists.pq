// Query: FlattenSharePointLookupLists
let
    Source = (spList as table, optional ColumnsToRemove as nullable list) as table =>
let
    ColumnTypes = Table.Schema(spList),

    // Detect lookup columns semantically
    RawLookupColumns = Table.SelectRows(ColumnTypes, each [NativeTypeName] = "Lookup")[Name],

    // Validate real list behavior
    ListColumns =
        List.Select(
            RawLookupColumns,
            (col) =>
                let
                    vals = List.RemoveNulls(Table.Column(spList, col)),
                    sample = try vals{0} otherwise null
                in
                    Value.Is(sample, type list)
        ),

    // Expand only true lists
    ExpandLists =
        List.Accumulate(
            ListColumns,
            spList,
            (state, current) =>
                try Table.ExpandListColumn(state, current) otherwise state
        ),

    // Extract only lookupValue and convert to text
    ExpandRecords =
        List.Accumulate(
            ListColumns,
            ExpandLists,
            (state, current) =>
                Table.TransformColumns(
                    state,
                    {
                        {
                            current,
                            (x) =>
                                try Text.From(x[lookupValue])
                                otherwise null,
                            type text
                        }
                    }
                )
        ),

    // Optional cleanup
    Removed =
        if ColumnsToRemove <> null then
            Table.RemoveColumns(ExpandRecords, List.Intersect({ColumnsToRemove, Table.ColumnNames(#"ExpandRecords")}))
        else
            ExpandRecords
in
    Removed
in
    Source