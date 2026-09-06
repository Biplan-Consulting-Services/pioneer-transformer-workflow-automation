// Query: Archive FRM13
let
    // Setting variables
    PartsStatusDateName = "Parts Status Change Date",
    EngineeringRequiredDateName = "Engineering Required Change Date",
    DesignerO = "Designer O Chande Date",
    DesignerF = "Designer F Chande Date",
    PrelimDWGProgr = "Prelim. DWG Progr. Chande Date",
    DWGInternVerif = "DWG Intern. Verif. Chande Date",
    FabDWGProgr = "Fab. DWG Progr. Chande Date",
    DWGInternVerif2 = "DWG Intern. Verif. 2 Chande Date",
    TCQProgress = "TCQ Progress Chande Date",
    NeedResubDWGDateName = "Need to Resub. DWG? Change Date",
    FabDWGIssuedDateDateName = "Fab. DWG Issued (date) Change Date",
    JobStateName = "Job State Change Date",

    // Load Archive Table
    #"Local Source Exists" = try Excel.CurrentWorkbook(){[Name="TableArchiveFRM13"]}[Content] otherwise null,
    
    // Load Active Table
    ActiveTable = TrackRemoteTable("FRM13-Auto", "TableOrders", "TableArchiveFRM13", "Order"),
    #"Changed Type ActiveTable" = Table.TransformColumnTypes(ActiveTable,{{"Order", type text}}),
    // Set Archive Table
    ArchiveTable = if #"Local Source Exists" <> null then #"Local Source Exists" else #"Changed Type ActiveTable",
    #"Changed Type ArchiveTable" = Table.TransformColumnTypes(ArchiveTable,{{"Order", type text}}),
    // Merge tables using a common key
    MergedTable = Table.NestedJoin(#"Changed Type ActiveTable", {"Order"}, #"Changed Type ArchiveTable", {"Order"}, "ActiveTable", JoinKind.LeftOuter),
    ExpandedTable  = Table.ExpandTableColumn(MergedTable, "ActiveTable", {"Parts Status", "Engineering Required", "Designer O", "Designer F", "Prelim. DWG Progr.", "DWG Intern. Verif.", "Fab. DWG Progr.", "DWG Intern. Verif. 2", "TQC Progress", "Need to Resub. DWG?", "Fab. DWG Issued (date)", "Job State"}, {"Parts Status.1", "Engineering Required.1", "Designer O.1", "Designer F.1", "Prelim. DWG Progr..1", "DWG Intern. Verif..1", "Fab. DWG Progr..1", "DWG Intern. Verif. 2.1", "TQC Progress.1", "Need to Resub. DWG?.1", "Fab. DWG Issued (date).1", "Job State.1"}),

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

    #"Added Column Designer O Change Date" =
        Table.AddColumn(#"Added Column Engineering Required Change Date", DesignerO & "-temp", each
            let
                Val1 = try [#"Designer O"] otherwise null,
                Val2 = try [#"Designer O.1"] otherwise null,
                Result = if Val1 <> null and Val2 <> null and Val1 <> Val2 then
                        DateTime.LocalNow()
                    else if Val1 <> null and Val2 = null then
                        DateTime.LocalNow()
                    else if Table.HasColumns(#"Added Column Engineering Required Change Date", DesignerO) then
                        Record.Field(_, DesignerO)
                    else
                        null
            in
                // Return the debugging information for key 20792
                Result
        ),

    #"Added Column Designer F Change Date" =
        Table.AddColumn(#"Added Column Designer O Change Date", DesignerF & "-temp", each
            let
                Val1 = try [#"Designer F"] otherwise null,
                Val2 = try [#"Designer F.1"] otherwise null,
                Result = if Val1 <> null and Val2 <> null and Val1 <> Val2 then
                        DateTime.LocalNow()
                    else if Val1 <> null and Val2 = null then
                        DateTime.LocalNow()
                    else if Table.HasColumns(#"Added Column Designer O Change Date", DesignerF) then
                        Record.Field(_, DesignerF)
                    else
                        null
            in
                // Return the debugging information for key 20792
                Result
        ),

    #"Added Column Prelim. DWG Progr. Change Date" =
        Table.AddColumn(#"Added Column Designer F Change Date", PrelimDWGProgr & "-temp", each
            let
                Val1 = try [#"Prelim. DWG Progr."] otherwise null,
                Val2 = try [#"Prelim. DWG Progr..1"] otherwise null,
                Result = if Val1 <> null and Val2 <> null and Val1 <> Val2 then
                        DateTime.LocalNow()
                    else if Val1 <> null and Val2 = null then
                        DateTime.LocalNow()
                    else if Table.HasColumns(#"Added Column Designer F Change Date", PrelimDWGProgr) then
                        Record.Field(_, PrelimDWGProgr)
                    else
                        null
            in
                // Return the debugging information for key 20792
                Result
        ),

    #"Added Column DWG Intern. Verif. Change Date" =
        Table.AddColumn(#"Added Column Prelim. DWG Progr. Change Date", DWGInternVerif & "-temp", each
            let
                Val1 = try [#"DWG Intern. Verif."] otherwise null,
                Val2 = try [#"DWG Intern. Verif..1"] otherwise null,
                Result = if Val1 <> null and Val2 <> null and Val1 <> Val2 then
                        DateTime.LocalNow()
                    else if Val1 <> null and Val2 = null then
                        DateTime.LocalNow()
                    else if Table.HasColumns(#"Added Column Prelim. DWG Progr. Change Date", DWGInternVerif) then
                        Record.Field(_, DWGInternVerif)
                    else
                        null
            in
                // Return the debugging information for key 20792
                Result
        ),

    #"Added Column Fab. DWG Progr. Change Date" =
        Table.AddColumn(#"Added Column DWG Intern. Verif. Change Date", FabDWGProgr & "-temp", each
            let
                Val1 = try [#"Fab. DWG Progr."] otherwise null,
                Val2 = try [#"Fab. DWG Progr..1"] otherwise null,
                Result = if Val1 <> null and Val2 <> null and Val1 <> Val2 then
                        DateTime.LocalNow()
                    else if Val1 <> null and Val2 = null then
                        DateTime.LocalNow()
                    else if Table.HasColumns(#"Added Column DWG Intern. Verif. Change Date", FabDWGProgr) then
                        Record.Field(_, FabDWGProgr)
                    else
                        null
            in
                // Return the debugging information for key 20792
                Result
        ),

    #"Added Column DWG Intern. Verif. 2 Change Date" =
        Table.AddColumn(#"Added Column Fab. DWG Progr. Change Date", DWGInternVerif2 & "-temp", each
            let
                Val1 = try [#"DWG Intern. Verif. 2"] otherwise null,
                Val2 = try [#"DWG Intern. Verif. 2.1"] otherwise null,
                Result = if Val1 <> null and Val2 <> null and Val1 <> Val2 then
                        DateTime.LocalNow()
                    else if Val1 <> null and Val2 = null then
                        DateTime.LocalNow()
                    else if Table.HasColumns(#"Added Column Fab. DWG Progr. Change Date", DWGInternVerif2) then
                        Record.Field(_, DWGInternVerif2)
                    else
                        null
            in
                // Return the debugging information for key 20792
                Result
        ),

    #"Added Column TCQ Progress Change Date" =
        Table.AddColumn(#"Added Column DWG Intern. Verif. 2 Change Date", TCQProgress & "-temp", each
            let
                Val1 = try [#"TCQ Progress"] otherwise null,
                Val2 = try [#"TCQ Progress.1"] otherwise null,
                Result = if Val1 <> null and Val2 <> null and Val1 <> Val2 then
                        DateTime.LocalNow()
                    else if Val1 <> null and Val2 = null then
                        DateTime.LocalNow()
                    else if Table.HasColumns(#"Added Column DWG Intern. Verif. 2 Change Date", TCQProgress) then
                        Record.Field(_, TCQProgress)
                    else
                        null
            in
                // Return the debugging information for key 20792
                Result
        ),

    #"Added Column Need to Resub. DWG? Change Date" =
        Table.AddColumn(#"Added Column TCQ Progress Change Date", NeedResubDWGDateName & "-temp", each
            let
                needToResubDWG = try [#"Need to Resub. DWG?"] otherwise null,
                needToResubDWG1 = try [#"Need to Resub. DWG?.1"] otherwise null,
                Result = if needToResubDWG <> null and needToResubDWG1 <> null and needToResubDWG <> needToResubDWG1 then
                        DateTime.LocalNow()
                    else if needToResubDWG <> null and needToResubDWG1 = null then
                        DateTime.LocalNow()
                    else if Table.HasColumns(#"Added Column TCQ Progress Change Date", NeedResubDWGDateName) then
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

    #"Added Column Job State Change Date" =
        Table.AddColumn(#"Added Column Fab. DWG Issued (date) Change Date", JobStateName & "-temp", each
            let
                JobState = try [#"Job State"] otherwise null,
                JobState1 = try [#"Job State.1"] otherwise null,
                Result = if JobState <> null and JobState1 <> null and JobState <> JobState1 then
                        DateTime.LocalNow()
                    else if JobState <> null and JobState1 = null then
                        DateTime.LocalNow()
                    else if Table.HasColumns(ExpandedTable, JobStateName) then
                        Record.Field(_, JobStateName)
                    else
                        null
            in
                // Return the debugging information for key 20792
                Result
        ),

    #"Removed Columns" = Table.RemoveColumns(#"Added Column Job State Change Date",{"Parts Status.1", "Engineering Required.1", "Designer O.1", "Designer F.1", "Prelim. DWG Progr..1", "DWG Intern. Verif..1", "Fab. DWG Progr..1", "DWG Intern. Verif. 2.1", "TQC Progress.1", "Need to Resub. DWG?.1", "Fab. DWG Issued (date).1", "Job State.1"}),
    #"Remove Old Columns" = if Table.HasColumns(#"Removed Columns", PartsStatusDateName) then Table.RemoveColumns(#"Removed Columns", {PartsStatusDateName, EngineeringRequiredDateName, NeedResubDWGDateName, FabDWGIssuedDateDateName, JobStateName}) else #"Removed Columns",
    #"Remove Old Columns 2" = if Table.HasColumns(#"Remove Old Columns", DesignerO) then Table.RemoveColumns(#"Remove Old Columns", {DesignerO, DesignerF, PrelimDWGProgr, DWGInternVerif,  FabDWGProgr, DWGInternVerif2, TCQProgress}) else #"Remove Old Columns",
    #"Rename ChangeDate" = Table.RenameColumns(#"Remove Old Columns 2", {{PartsStatusDateName & "-temp", PartsStatusDateName}, {EngineeringRequiredDateName & "-temp", EngineeringRequiredDateName}, {DesignerO & "-temp", DesignerO},{DesignerF & "-temp", DesignerF}, {PrelimDWGProgr & "-temp", PrelimDWGProgr}, {DWGInternVerif & "-temp", DWGInternVerif}, {FabDWGProgr & "-temp", FabDWGProgr}, {DWGInternVerif2 & "-temp", DWGInternVerif2}, {TCQProgress & "-temp", TCQProgress}, {NeedResubDWGDateName & "-temp", NeedResubDWGDateName}, {FabDWGIssuedDateDateName & "-temp", FabDWGIssuedDateDateName}, {JobStateName & "-temp", JobStateName}})
in
    #"Rename ChangeDate"