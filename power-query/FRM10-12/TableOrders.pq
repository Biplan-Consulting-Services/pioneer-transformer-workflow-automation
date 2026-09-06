// Query: TableOrders
let
    OrderMergeCols = {"Order Number", "Qty"},
    OrderFieldCols = {"Order Date", "Initial Promised Date", "PO", "Price Value", "Province/State", "WET-WETP", "Indexing", "Client", "PO Item #" /*, "Order"*/},

    ModelMergeCols = {"PO Item #"},
    ModelFieldCols = {
                        "JS #", "Technical Notes", "KVA and KV", "Primary Voltage", "Secondary Voltage",
                        "Type", "Oil Type", "Core",
                        "Phases", "Info+", "Protector & Switchgear Item #", "Oil Amount",
                        "Configuration", "Section Qty", "Cable", "Form", "Copper (LV)",
                        "Wire (HV)", "Overcoil", "Description"
                     },
    ModelAllCols = List.Combine({ModelMergeCols, ModelFieldCols}),

    Source = Table.TransformColumnTypes(Excel.CurrentWorkbook(){[Name="TableOrders"]}[Content], {{"Qty", type text}, {"Order", type text}, {"PO Item #", type text}}),
    #"Removed Formula Columns" = Table.RemoveColumns(Source, {"Estimated Delivery Date", "Price CAD", "Price USD", "Price", "Navigation Order", "Navigation Model"}),

    OriginalColumnOrder = Table.ColumnNames(#"Removed Formula Columns"),

    #"Added Order Number" = Table.AddColumn(Source, "Order Number", each Text.BeforeDelimiter([Order], "-")),
    #"Added SA Job Flag" = Table.AddColumn(#"Added Order Number", "SA Job", each Text.Contains([Order], "SA")),


    // Pulling the data from Sharepoint lists into a table with similar column names as FRM10-12
    #"Sharepoint Source" = Table.SelectColumns(Orders, {"Order Number", "Client", "Order Type", "Model", "Order Date", "Qty", "Initial Promised Date", "PO", "Price", "Province/State", "WET-WETP", "Indexing", "SA"}),
    #"Filtered Sharepoint Orders With Order Number" = Table.SelectRows(#"Sharepoint Source", each [Order Number] <> null and [Order Number] <> ""),
    // Rename + type, driven by ColumnMap.pq (entity "Orders")
    #"Applied Orders Column Map" = ApplyColumnMap(#"Filtered Sharepoint Orders With Order Number", "Orders"),
    #"Distinct Orders" = Table.Distinct(#"Applied Orders Column Map", OrderMergeCols),
    #"Added SA Job to Orders" = Table.AddColumn(#"Distinct Orders", "SA Job", each false),

    // Importing SA lines
    #"Filtered SA Orders" = Table.SelectRows(#"Distinct Orders", each [SA] <> null and [SA] = true),
    #"Added SA Job to SA Orders" = Table.AddColumn(#"Filtered SA Orders", "SA Job", each true),
    #"Replaced SA model numbers" = Table.TransformColumns(#"Added SA Job to SA Orders", {
        {"PO Item #", each if _ = null then _ else if Text.EndsWith(_, " SA") then _ else _ & " SA", type text},
        {"Price Value", each null, type any}
    }),
    #"Complete Imported Orders" = Table.Combine({#"Added SA Job to Orders", #"Replaced SA model numbers"}, {"Order Number", "Client", "Order Type", "Order Date", "Qty", "Initial Promised Date", "PO", "Price Value", "Province/State", "WET-WETP", "Indexing", "PO Item #", "SA Job"}),

    // Importing models from Sharepoint and combining to a single table
    // Technical spec fields (JS #, kVA, voltages, oil/core type, phases, cable/form/coil, description)
    // moved from "Models" into "Model Revisions" — Models now only keeps identity/workflow fields
    // plus "Latest Model Revision", a pointer to the current row in Model Revisions.
    ModelRevisionSpecCols = {"JS #", "Model Type", "Model Description", "kVA", "Primary Voltage", "Secondary Voltage", "Oil Type", "Oil Amount", "Core Type", "Phases", "Cable", "Form", "Copper (LV)", "Wire (HV)", "Overcoil"},
    StaleModelSpecCols = {"JS #", "Model Type", "Description", "kVA and kV", "Oil Type", "Oil Amount", "Core Type", "Phases", "Cable", "Form", "Copper (LV)", "Wire (HV)", "Overcoil"},
    #"Removed Stale Model Spec Columns" = Table.RemoveColumns(Models, StaleModelSpecCols, MissingField.Ignore),
    #"Merged Model Revisions" = Table.NestedJoin(#"Removed Stale Model Spec Columns", {"Latest Model Revision"}, #"Model Revisions", {"Model_Revion_ID"}, "Revision", JoinKind.LeftOuter),
    #"Expanded Model Revisions" = Table.ExpandTableColumn(#"Merged Model Revisions", "Revision", ModelRevisionSpecCols, ModelRevisionSpecCols),
    // "Model Description" became a multi-choice list in Model Revisions (was a single Choice field on Models)
    #"Flattened Model Description" = Table.TransformColumns(#"Expanded Model Revisions", {"Model Description", each try Text.Combine(List.Transform(_, Text.From), ", ") otherwise null, type text}),

    // Rename + type, driven by ColumnMap.pq (entities "Models" and "Model Revisions" -
    // both apply here since this table already carries fields from both sources).
    #"Imported Base Models" = ApplyColumnMap(ApplyColumnMap(#"Flattened Model Description", "Models"), "Model Revisions"),
    #"Complete Imported Models" = Table.SelectColumns(#"Imported Base Models", ModelAllCols),

    ApplyPrefixedOverrides = (SourceTable as table, MergeCols as list, FieldCols as list, Prefix as text) as table =>
    let
        PrefixedMergeCols = List.Transform(MergeCols, each Prefix & Text.From(_)),
        PrefixedFieldCols = List.Transform(FieldCols, each Prefix & Text.From(_)),
        PrefixedAllCols = List.Combine({PrefixedMergeCols, PrefixedFieldCols}),
        TargetAllCols = List.Combine({MergeCols, FieldCols}),

        // Fail fast with a clear message instead of a cryptic "field not found" deep in the
        // per-row loop below. This happens when a field is added to MergeCols/FieldCols
        // before the matching sp.-prefixed column actually exists on SourceTable (which only
        // has sp.-prefixed columns for fields common to both the SharePoint data and the
        // existing Excel table - see SharepointCommonColumns/ModelsSharepointCommonColumns).
        MissingCols = List.Difference(PrefixedAllCols, Table.ColumnNames(SourceTable)),
        Checked =
            if List.Count(MissingCols) > 0 then
                let
                    MissingTargetNames = List.Transform(MissingCols, each Text.Range(_, Text.Length(Prefix)))
                in
                    error Error.Record(
                        "ApplyPrefixedOverrides.MissingColumns",
                        "Expected column(s) " &
                            Text.Combine(List.Transform(MissingTargetNames, each """" & _ & """"), ", ") &
                            " to be present (as """ & Prefix & """-prefixed columns) on the source table, but they weren't found. " &
                            "This means a field was added to the merge/field column list before the matching column exists on " &
                            "the TableOrders Excel table - add the column there first, then this will resolve on the next refresh.",
                        [MissingColumns = MissingTargetNames]
                    )
            else
                SourceTable,

        // Avoids the classic Power Query anti-pattern of Table.ToRecords -> per-row
        // List.Transform -> Table.FromRecords, which forces the whole table into a
        // list-of-records copy and back. Table.AddColumn + Table.ExpandRecordColumn do the
        // exact same per-row logic (same joinFound check, same Record.SelectFields/
        // Record.RenameFields) without that full-table round trip.
        #"Added Overrides" = Table.AddColumn(Checked, "___Overrides___", (r) =>
            let
                joinFound =
                    List.AllTrue(
                        List.Transform(
                            PrefixedMergeCols,
                            (col) => Record.FieldOrDefault(r, col) <> null
                        )
                    )
            in
                if joinFound
                then Record.RenameFields(Record.SelectFields(r, PrefixedAllCols), List.Zip({PrefixedAllCols, TargetAllCols}))
                else Record.SelectFields(r, TargetAllCols)
        ),
        #"Removed Original Target Columns" = Table.RemoveColumns(#"Added Overrides", TargetAllCols),
        #"Expanded Overrides" = Table.ExpandRecordColumn(#"Removed Original Target Columns", "___Overrides___", TargetAllCols),
        #"Removed sp Columns" = Table.RemoveColumns(#"Expanded Overrides", List.Select(Table.ColumnNames(#"Expanded Overrides"), each Text.Contains(_, Prefix)))
    in
        #"Removed sp Columns",

    // Differential update for Orders
    SharepointCommonColumns = List.Intersect({Table.ColumnNames(#"Complete Imported Orders"), Table.ColumnNames(#"Added SA Job Flag")}),
    PrefixedSharepointCommonColumns = List.Transform(SharepointCommonColumns, each "sp." & Text.From(_)),

    #"Merged Orders With Sharepoint Data" = Table.NestedJoin(#"Added SA Job Flag", {"Order Number", "Qty", "SA Job"}, #"Complete Imported Orders", {"Order Number", "Qty", "SA Job"}, "SharepointList", JoinKind.LeftOuter),
    #"Expanded Sharepoint Order Fields" = Table.ExpandTableColumn(#"Merged Orders With Sharepoint Data", "SharepointList", SharepointCommonColumns, PrefixedSharepointCommonColumns),

    #"Applied Sharepoint Order Overrides" = ApplyPrefixedOverrides(#"Expanded Sharepoint Order Fields", OrderMergeCols, OrderFieldCols, "sp."),

    // Differential update for Models
    ModelsSharepointCommonColumns = List.Intersect({Table.ColumnNames(#"Complete Imported Models"), Table.ColumnNames(#"Added SA Job Flag")}),
    ModelsPrefixedSharepointCommonColumns = List.Transform(ModelsSharepointCommonColumns, each "sp." & Text.From(_)),

    #"Merged Orders With Sharepoint Models" = Table.NestedJoin(#"Applied Sharepoint Order Overrides", ModelMergeCols, #"Complete Imported Models", ModelMergeCols, "SharepointList", JoinKind.LeftOuter),
    #"Expanded Sharepoint Model Fields" = Table.ExpandTableColumn(#"Merged Orders With Sharepoint Models", "SharepointList", ModelsSharepointCommonColumns, ModelsPrefixedSharepointCommonColumns),

    #"Applied Sharepoint Model Overrides" = ApplyPrefixedOverrides(#"Expanded Sharepoint Model Fields", ModelMergeCols, ModelFieldCols, "sp."),

    // Building table of orders not yet added to FRM10-12
    #"Merged Sharepoint Orders With Existing Table" = Table.NestedJoin(#"Complete Imported Orders", {"Order Number", "Qty", "SA Job"}, #"Added SA Job Flag", {"Order Number", "Qty", "SA Job"}, "TableToList", JoinKind.LeftOuter),
    #"Expanded Match Flag" = Table.ExpandTableColumn(#"Merged Sharepoint Orders With Existing Table", "TableToList", {"Order Number"}, {"TableToList.Order Number"}),
    #"Filtered New Orders" = Table.SelectRows(#"Expanded Match Flag", each [TableToList.Order Number] = null),
    #"Merged Models to New Orders" = Table.NestedJoin(#"Filtered New Orders", ModelMergeCols, #"Complete Imported Models", ModelMergeCols, "SharepointList", JoinKind.LeftOuter),
    #"Expanded Models to New Orders" = Table.ExpandTableColumn(#"Merged Models to New Orders", "SharepointList", ModelFieldCols, ModelFieldCols),

    // Expanding new orders into  multiple rows for Jobs and SAs
    // Qty is text and not guaranteed numeric (see ColumnMap.pq) - a non-numeric Qty
    // yields zero job rows rather than crashing this whole branch.
    #"Added Job Index List" = Table.AddColumn(#"Expanded Models to New Orders", "Jobs", each {1..(try Number.FromText([Qty]) otherwise 0)}),
    #"Expanded Jobs" = Table.ExpandListColumn(#"Added Job Index List", "Jobs"),
    #"Added Order Column" = Table.AddColumn(#"Expanded Jobs", "Order", each Text.From([Order Number]) & "-" & Text.From([Jobs]) & "/" & Text.From([Qty]) & (if [SA Job] = true then " SA" else ""), type text),
    #"Removed New Order Helper Columns" = Table.RemoveColumns(#"Added Order Column",{"TableToList.Order Number", "Jobs"}),

    // Combining existing and new rows
    #"Combined Existing And New Orders" = Table.Combine({#"Applied Sharepoint Model Overrides", #"Removed New Order Helper Columns"}),

    // Purging logic to remove rows once archived
    #"Merged With Archived Orders" = Table.NestedJoin(#"Combined Existing And New Orders", {"Order"}, ArchivedOrders, {"Order"}, "ArchivedOrders", JoinKind.LeftOuter),
    #"Expanded Archive Fields" = Table.ExpandTableColumn(#"Merged With Archived Orders", "ArchivedOrders", {"Location", "Delivery Date"}, {"ArchivedOrders.Location", "ArchivedOrders.Delivery Date"}),
    #"Changed Archive Delivery Date Type" = Table.TransformColumnTypes(#"Expanded Archive Fields",{{"ArchivedOrders.Delivery Date", type date}}),
    #"Filtered Out Archived Orders" = Table.SelectRows(#"Changed Archive Delivery Date Type", each not (
        ([ArchivedOrders.Location] = "LI"
        and
        Date.From([ArchivedOrders.Delivery Date]) <> null) or [ArchivedOrders.Location] = "AN"
    )),
    #"Remove Archive Columns" = Table.RemoveColumns(#"Filtered Out Archived Orders", {"ArchivedOrders.Location", "ArchivedOrders.Delivery Date"}),
    #"Filtered Non Empty Orders" = Table.SelectRows(#"Remove Archive Columns", each [Order] <> null and [Order] <> ""),

    // Grab the merge from client lead times table (could just be a lookup?)
    #"Removed Stale Lead Time Column" = Table.RemoveColumns(#"Filtered Non Empty Orders",{"Lead Time"}),
    #"Merged With Client Lead Times" = Table.NestedJoin(#"Removed Stale Lead Time Column", {"Client"}, ClientLeadTimes, {"Client"}, "ClientLeadTimes", JoinKind.LeftOuter),
    #"Expanded Client Lead Times" = Table.ExpandTableColumn(#"Merged With Client Lead Times", "ClientLeadTimes", {"Lead Time"}, {"Lead Time"}),
    #"Defaulted Missing Lead Time" = Table.ReplaceValue(#"Expanded Client Lead Times",null, 26, Replacer.ReplaceValue,{"Lead Time"}),

    // Sets Ing. Due Date according to rule
    #"Removed Stale Ing Due Date Column" = Table.RemoveColumns(#"Defaulted Missing Lead Time", {"Ing. Due Date"}),
    #"Added Ing Due Date" = Table.AddColumn(
        #"Removed Stale Ing Due Date Column",
        "Ing. Due Date",
        each
            let
                baseDate = if [Tanking Date] <> null and [Tanking Date] <> "" then [Tanking Date] else [Initial Promised Date],
                leadTime = [Lead Time]
            in
                try Date.AddDays(baseDate, -1 * ((leadTime + 4) * 7)) otherwise null
    ),

    // Grab the merge from BO table (could just be a lookup?)
    #"Removed Stale BO Column" = Table.RemoveColumns(#"Added Ing Due Date",{"BO"}),
    #"Merged With Back Orders" = Table.NestedJoin(#"Removed Stale BO Column", {"Order"}, BackOrders, {"Order"}, "BackOrders", JoinKind.LeftOuter),
    #"Expanded Back Order Status" = Table.ExpandTableColumn(#"Merged With Back Orders", "BackOrders", {"BO"}, {"BO"}),
    #"Removed Duplicates" = Table.Distinct(#"Expanded Back Order Status", {"Order"}),

    // Final pass to ensrue data schema integrity
    #"Removed Empty Order Number" = Table.SelectRows(#"Removed Duplicates", each [Order Number] <> null and [Order Number] <> ""),
    #"Selected Original Columns" = Table.SelectColumns(#"Removed Empty Order Number", OriginalColumnOrder),
    #"Reordered Table" = Table.ReorderColumns(#"Selected Original Columns", OriginalColumnOrder)
in
    #"Reordered Table"