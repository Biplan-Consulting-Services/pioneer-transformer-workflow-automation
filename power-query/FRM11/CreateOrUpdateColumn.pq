// Query: CreateOrUpdateColumn
let
    createOrUpdateColumn = (tbl as table, colName as text, colExpression as function, optional colType as type) as table =>
        let
            // Remove the column if it exists
            tableWithRemovedColumn = try Table.RemoveColumns(tbl, {colName}) otherwise tbl,
            // Add the column with the provided expression
            tableWithNewColumn = Table.AddColumn(tableWithRemovedColumn, colName, each colExpression(_)),
            // Set the column type if provided, else return the table as is
            tableWithTypedColumn = if colType <> null then Table.TransformColumnTypes(tableWithNewColumn, {{colName, colType}}) else tableWithNewColumn
        in
            tableWithTypedColumn
in
    createOrUpdateColumn