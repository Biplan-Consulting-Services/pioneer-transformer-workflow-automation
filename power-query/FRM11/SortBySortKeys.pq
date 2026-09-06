// Query: SortBySortKeys
// Function to sort table based on 'Sort Key X' columns
(SourceTable as table) as table =>
let
    // Step 1: Get all columns with the name pattern 'Sort Key X'
    SortKeyColumns = List.Select(Table.ColumnNames(SourceTable), each Text.StartsWith(_, "Sort Key")),
    
    // Step 2: Sort the table based on the identified Sort Key columns
    SortedTable = Table.Sort(SourceTable, List.Transform(SortKeyColumns, each {_, Order.Ascending}))
in
    SortedTable