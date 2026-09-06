// Query: AddMultipleNullColumns
let
    AddMultipleColumns = (inputTable as table, columnNames as list) as table =>
    let
        // Function to add a single column with a default value of null
        AddColumn = (tbl as table, colName as text) =>
            Table.AddColumn(tbl, colName, each null),
        
        // Add all columns specified in columnNames
        Result = List.Accumulate(
            columnNames,
            inputTable,
            (state, current) => AddColumn(state, current)
        )
    in
        Result
in
    AddMultipleColumns