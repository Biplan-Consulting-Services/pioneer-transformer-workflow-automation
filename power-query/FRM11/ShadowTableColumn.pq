// Query: ShadowTableColumn
let
    Source = (dataset as table, shadowingColumnName as text, shadowedColumnName as text, updateColumnName as text, refreshRateDays as number) =>
let
    Source = dataset,
    ColumnNames = Table.ColumnNames(Source),
    ShadowedColumnExists = List.Contains(ColumnNames, shadowedColumnName),
    ShadowingColumnExists = List.Contains(ColumnNames, shadowingColumnName),
    UpdateColumnExists = List.Contains(ColumnNames, updateColumnName),
    CanApplyFunction = ShadowedColumnExists,
    Today = DateTime.Date(DateTime.LocalNow()),

    UpdateShadowingColumn = (row) =>
        let
            updateDate = Record.Field(row, updateColumnName),
            dateDiff = if updateDate = null then null else Duration.From(Today - updateDate) / #duration(1,0,0,0),  // calculate the difference in days
            shouldRefresh = updateDate = null or dateDiff >= refreshRateDays,
            updatedUpdateDate = if shouldRefresh then Today else updateDate
        in
            if shouldRefresh then Record.TransformFields(row, {{shadowingColumnName, each Record.Field(row, shadowedColumnName)}, {updateColumnName, each Today}}) else row,
    
    
    UpdatedSource =
        if not CanApplyFunction then
            // Cannot shadow the given column, it doesn't exist.
            Source
        else
            let 
                // Add blank columns if they don't exist
                #"Added Shadowing Column" = if not ShadowingColumnExists then Table.AddColumn(Source, shadowingColumnName, each null, type any) else Source,
                #"Added Update Column" = if not UpdateColumnExists then Table.AddColumn(#"Added Shadowing Column", updateColumnName, each null, type any) else #"Added Shadowing Column",
                ShadowedColumnType = Value.Type(Table.Column(#"Added Update Column", shadowedColumnName){0}),
                ShadowedColumnTypeNonNull = if ShadowedColumnType = Null.Type then type any else ShadowedColumnType, 
                #"Changed Type" = Table.TransformColumnTypes(#"Added Update Column", {{shadowingColumnName, ShadowedColumnTypeNonNull}, {updateColumnName, type date}}),
                #"Updated Shadowed Columns" = Table.TransformRows(#"Changed Type", UpdateShadowingColumn),
                #"Parsed Table From Records" = Table.FromRecords(#"Updated Shadowed Columns")
            in
                #"Parsed Table From Records"
in
    UpdatedSource
in
    Source