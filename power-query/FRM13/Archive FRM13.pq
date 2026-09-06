// Query: Archive FRM13
let
    // Setting variables
    PartsStatusDateName = "Parts Status Change Date",
    EngineeringRequiredDateName = "Engineering Required Change Date",
    NeedResubDWGDateName = "Need to Resub. DWG? Change Date",
    FabDWGIssuedDateDateName = "Fab. DWG Issued (date) Change Date",

    // Load Archive Table
    #"Local Source Exists" = try Excel.CurrentWorkbook(){[Name="TableArchiveFRM13"]}[Content] otherwise null,
    
    // Load Active Table
    ActiveTable = TrackRemoteTable("FRM13-Auto", "TableOrders", "TableArchiveFRM13", "Order"),
    #"Changed Type" = Table.TransformColumnTypes(ActiveTable,{{"Order", type text}}),
    // Set Archive Table
    ArchiveTable = if #"Local Source Exists" <> null then #"Local Source Exists" else #"Changed Type",
    // Merge tables using a common key
    MergedTable = Table.NestedJoin(#"Changed Type", {"Order"}, ArchiveTable, {"Order"}, "ActiveTable", JoinKind.LeftOuter),
    ExpandedTable  = Table.ExpandTableColumn(MergedTable, "ActiveTable", {"Parts Status", "Engineering Required", "Need to Resub. DWG?", "Fab. DWG Issued (date)"}, {"Parts Status.1", "Engineering Required.1", "Need to Resub. DWG?.1", "Fab. DWG Issued (date).1"}),

    // Add custom columns for change detection
    #"Added Column Parts Status Change Date" =
        Table.AddColumn(ExpandedTable, PartsStatusDateName & "-temp", each
            let
                PartStatus = try [#"Parts Status"] otherwise null,
                PartStatus1 = try [#"Parts Status.1"] otherwise null,
                Result = if PartStatus <> null and PartStatus1 <> null and PartStatus <> PartStatus1 then
                        DateTime.LocalNow()
                    else if PartStatus <> null and PartStatus1 = null then
                        DateTime.LocalNow()
                    else if Table.HasColumns(ExpandedTable, PartsStatusDateName) then
                        Record.Field(_, PartsStatusDateName)
                    else
                        null
            in
                // Return the debugging information for key 20792
                Result
        ),

    #"Added Column Engineering Required Change Date" =
        Table.AddColumn(#"Added Column Parts Status Change Date", EngineeringRequiredDateName & "-temp", each
            let
                EngReq = try [#"Engineering Required"] otherwise null,
                EngReq1 = try [#"Engineering Required.1"] otherwise null,
                Result = if EngReq <> null and EngReq1 <> null and EngReq <> EngReq1 then
                        DateTime.LocalNow()
                    else if EngReq <> null and EngReq1 = null then
                        DateTime.LocalNow()
                    else if Table.HasColumns(#"Added Column Parts Status Change Date", EngineeringRequiredDateName) then
                        Record.Field(_, EngineeringRequiredDateName)
                    else
                        null
            in
                // Return the debugging information for key 20792
                Result
        ),

    #"Added Column Need to Resub. DWG? Change Date" =
        Table.AddColumn(#"Added Column Engineering Required Change Date", NeedResubDWGDateName & "-temp", each
            let
                needToResubDWG = try [#"Need to Resub. DWG?"] otherwise null,
                needToResubDWG1 = try [#"Need to Resub. DWG?.1"] otherwise null,
                Result = if needToResubDWG <> null and needToResubDWG1 <> null and needToResubDWG <> needToResubDWG1 then
                        DateTime.LocalNow()
                    else if needToResubDWG <> null and needToResubDWG1 = null then
                        DateTime.LocalNow()
                    else if Table.HasColumns(#"Added Column Engineering Required Change Date", NeedResubDWGDateName) then
                        Record.Field(_, NeedResubDWGDateName)
                    else
                        null
            in
                // Return the debugging information for key 20792
                Result
        ),
        
    #"Added Column Fab. DWG Issued (date) Change Date" =
        Table.AddColumn(#"Added Column Need to Resub. DWG? Change Date", FabDWGIssuedDateDateName & "-temp", each
            let
                FabDWGIssued = try [#"Fab. DWG Issued (date)"] otherwise null,
                FabDWGIssued1 = try [#"Fab. DWG Issued (date).1"] otherwise null,
                Result = if FabDWGIssued <> null and FabDWGIssued1 <> null and FabDWGIssued <> FabDWGIssued1 then
                        DateTime.LocalNow()
                    else if FabDWGIssued <> null and FabDWGIssued1 = null then
                        DateTime.LocalNow()
                    else if Table.HasColumns(#"Added Column Need to Resub. DWG? Change Date", FabDWGIssuedDateDateName) then
                        Record.Field(_, FabDWGIssuedDateDateName)
                    else
                        null
            in
                // Return the debugging information for key 20792
                Result
        ),
    #"Changed Type1" = Table.TransformColumnTypes(#"Added Column Fab. DWG Issued (date) Change Date",{{"Order", type text}}),
    #"Change Date Merge" = Table.NestedJoin(#"Changed Type", {"Order"}, #"Changed Type1", {"Order"}, "ChangeDate", JoinKind.LeftOuter),
    #"Remove Old Columns" = if Table.HasColumns(#"Change Date Merge", PartsStatusDateName) then Table.RemoveColumns(#"Change Date Merge", {PartsStatusDateName, EngineeringRequiredDateName, NeedResubDWGDateName, FabDWGIssuedDateDateName}) else #"Change Date Merge",
    #"Expanded ChangeDate" = Table.ExpandTableColumn(#"Remove Old Columns", "ChangeDate", List.Transform({PartsStatusDateName, EngineeringRequiredDateName, NeedResubDWGDateName, FabDWGIssuedDateDateName}, each _ & "-temp"),{PartsStatusDateName, EngineeringRequiredDateName, NeedResubDWGDateName, FabDWGIssuedDateDateName})
in
    #"Expanded ChangeDate"