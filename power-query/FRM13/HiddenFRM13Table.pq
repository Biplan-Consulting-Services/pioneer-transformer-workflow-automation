// Query: HiddenFRM13Table
let
    Source = Excel.CurrentWorkbook(){[Name="HiddenFRM13Table"]}[Content],
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"Order", type text}, {"Qty", Int64.Type}, {"PO Item #", type any}, {"Parts Status", type any}, {"KVA and KV", type any}, {"Type", type text}, {"Client", type text}, {"Order Date", Int64.Type}, {"Duplicate", type text}, {"Engineering Required", type text}, {"Stack Core", type text}, {"Designer O", type text}, {"Designer F", type text}, {"Promised Date of DWG Issue", Int64.Type}, {"Special Promised date (date or code)", type any}, {"Prelim. DWG Progr.", type text}, {"DWG Intern. Verif.", type any}, {"Prelim. DWG Issued (date)", Int64.Type}, {"Client Comments Due Date (date)", Int64.Type}, {"Need to Resub. DWG?", type text}, {"General Arrang. DWG Approved (date)", Int64.Type}, {"Fab. DWG Progr.", type text}, {"DWG Intern. Verif. 2", type any}, {"Fab. DWG Issued (date)", type any}, {"TQC Progress", type text}, {"Initial Promised Date", Int64.Type}, {"Manual Priority", type any}, {"Priority", Int64.Type}, {"Client Desired Date", type any}, {"Tanking Date", Int64.Type}, {"Fournisseur CUVE", type text}, {"Ing Due Date (Tank -LT appro - 4 wks)", Int64.Type}, {"Comments", type any}, {"Lead time", Int64.Type}, {"Estimated Effort Left", type number}, {"Job State", type text}}),
    
    // Merge Static Table with Editable Table
    #"Merged Queries" = Table.NestedJoin(ManualDataUpdate, {"Order"}, #"Changed Type", {"Order"}, "TableOrders", JoinKind.LeftOuter),
    #"Expanded TableOrders" = Table.ExpandTableColumn(#"Merged Queries", "TableOrders", {"Qty", "Qty-Change Date", "PO Item #", "PO Item #-Change Date", "Parts Status", "Parts Status-Change Date", "KVA and KV", "KVA and KV-Change Date", "Type", "Type-Change Date", "Client", "Client-Change Date", "Order Date", "Order Date-Change Date", "Duplicate", "Duplicate-Change Date", "Engineering Required", "Engineering Required-Change Date", "Stack Core", "Stack Core-Change Date", "Designer O", "Designer O-Change Date", "Designer F", "Designer F-Change Date", "Promised Date of DWG Issue", "Promised Date of DWG Issue-Change Date", "Special Promised date (date or code)", "Special Promised date (date or code)-Change Date", "Prelim. DWG Progr.", "Prelim. DWG Progr.-Change Date", "DWG Intern. Verif.", "DWG Intern. Verif.-Change Date", "Prelim. DWG Issued (date)", "Prelim. DWG Issued (date)-Change Date", "Client Comments Due Date (date)", "Client Comments Due Date (date)-Change Date", "Need to Resub. DWG?", "Need to Resub. DWG?-Change Date", "General Arrang. DWG Approved (date)", "General Arrang. DWG Approved (date)-Change Date", "Fab. DWG Progr.", "Fab. DWG Progr.-Change Date", "DWG Intern. Verif. 2", "DWG Intern. Verif. 2-Change Date", "Fab. DWG Issued (date)", "Fab. DWG Issued (date)-Change Date", "TQC Progress", "TQC Progress-Change Date", "Initial Promised Date", "Initial Promised Date-Change Date", "Manual Priority", "Manual Priority-Change Date", "Priority", "Priority-Change Date", "Client Desired Date", "Client Desired Date-Change Date", "Tanking Date", "Tanking Date-Change Date", "Fournisseur CUVE", "Fournisseur CUVE-Change Date", "Ing Due Date (Tank -LT appro - 4 wks)", "Ing Due Date (Tank -LT appro - 4 wks)-Change Date", "Comments", "Comments-Change Date", "Lead time", "Lead time-Change Date", "Estimated Effort Left", "Estimated Effort Left-Change Date", "Job State", "Job State-Change Date"}, {"Qty.1", "Qty-Change Date", "PO Item #.1", "PO Item #-Change Date", "Parts Status.1", "Parts Status-Change Date", "KVA and KV.1", "KVA and KV-Change Date", "Type.1", "Type-Change Date", "Client.1", "Client-Change Date", "Order Date.1", "Order Date-Change Date", "Duplicate.1", "Duplicate-Change Date", "Engineering Required.1", "Engineering Required-Change Date", "Stack Core.1", "Stack Core-Change Date", "Designer O.1", "Designer O-Change Date", "Designer F.1", "Designer F-Change Date", "Promised Date of DWG Issue.1", "Promised Date of DWG Issue-Change Date", "Special Promised date (date or code).1", "Special Promised date (date or code)-Change Date", "Prelim. DWG Progr..1", "Prelim. DWG Progr.-Change Date", "DWG Intern. Verif..1", "DWG Intern. Verif.-Change Date", "Prelim. DWG Issued (date).1", "Prelim. DWG Issued (date)-Change Date", "Client Comments Due Date (date).1", "Client Comments Due Date (date)-Change Date", "Need to Resub. DWG?.1", "Need to Resub. DWG?-Change Date", "General Arrang. DWG Approved (date).1", "General Arrang. DWG Approved (date)-Change Date", "Fab. DWG Progr..1", "Fab. DWG Progr.-Change Date", "DWG Intern. Verif. 2.1", "DWG Intern. Verif. 2-Change Date", "Fab. DWG Issued (date).1", "Fab. DWG Issued (date)-Change Date", "TQC Progress.1", "TQC Progress-Change Date", "Initial Promised Date.1", "Initial Promised Date-Change Date", "Manual Priority.1", "Manual Priority-Change Date", "Priority.1", "Priority-Change Date", "Client Desired Date.1", "Client Desired Date-Change Date", "Tanking Date.1", "Tanking Date-Change Date", "Fournisseur CUVE.1", "Fournisseur CUVE-Change Date", "Ing Due Date (Tank -LT appro - 4 wks).1", "Ing Due Date (Tank -LT appro - 4 wks)-Change Date", "Comments.1", "Comments-Change Date", "Lead time.1", "Lead time-Change Date", "Estimated Effort Left.1", "Estimated Effort Left-Change Date", "Job State.1", "Job State-Change Date"}),
    // Get column names that need tracking (excluding "Order")
    ColumnNames = List.RemoveItems(Table.ColumnNames(ManualDataUpdate), {"Order"}),

    // Function to update the timestamp column based on changes
    UpdateTimestamp = (currentRow as record, columnName as text) =>
    let
        oldValue = try Record.Field(currentRow, columnName & "-Change Date") otherwise null,
        prevValue = try Record.Field(currentRow, columnName & ".1") otherwise null,
        newValue = try Record.Field(currentRow, columnName) otherwise null,

        // Proper null checks
        isPrevNull = prevValue = null,
        isNewNull = newValue = null,

        newTimestamp = if ( prevValue <> null and newValue <> null and prevValue <> newValue ) then
                        DateTime.LocalNow()
                    else if (( prevValue <> null and newValue = null) or (newValue <> null and prevValue = null)) then
                        DateTime.LocalNow()
                    else
                        oldValue
    in
        newTimestamp,

    // Add timestamp columns for each tracked column
    TableWithTimestamps = List.Accumulate(ColumnNames, #"Expanded TableOrders", 
        (state, column) => Table.AddColumn(state, column & "-Change Date.2", each UpdateTimestamp(_, column), type nullable datetime)),

    // Remove duplicated columns (keep only one set)
    ColumnsToRemove = List.Select(Table.ColumnNames(TableWithTimestamps), each Text.EndsWith(_, ".1")),
    CleanedTable = Table.RemoveColumns(TableWithTimestamps, ColumnsToRemove),
    ColumnsToRemove2 = List.Select(Table.ColumnNames(CleanedTable), each Text.EndsWith(_, "-Change Date")),
    CleanedTable2 = Table.RemoveColumns(CleanedTable, ColumnsToRemove2),
    // Get all columns that end in ".2"
    ColumnsWithDot2 = List.Select(Table.ColumnNames(CleanedTable2), each Text.EndsWith(_, ".2")),

    // Create rename pairs: {"Order.2", "Order"}, {"Qty.2", "Qty"}, etc.
    RenamePairs = List.Transform(ColumnsWithDot2, each {_, Text.BeforeDelimiter(_, ".2")}),

    RenamedTable = Table.RenameColumns(CleanedTable2, RenamePairs, MissingField.Ignore),

    // === Reorder Columns ===
    AllColumns = Table.ColumnNames(RenamedTable),
    BaseColumns = List.Select(AllColumns, each not Text.EndsWith(_, "-Change Date") and _ <> "Order"),
    OrderedColumns = List.Combine(List.Transform(BaseColumns, each {_, _ & "-Change Date"})),
    FinalColumnOrder = List.InsertRange(OrderedColumns, 0, {"Order"}),
    OrderedTable = Table.ReorderColumns(RenamedTable, FinalColumnOrder)

in
    OrderedTable