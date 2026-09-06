// Query: TableOrders
let
    Source = ImportFromIndex("FRM10-12", "TableOrders"),
    FilteredRows = Table.SelectRows(Source, each ([Order] <> null and [Order] <> "" and [Order] <> "OS")),
    #"Split Column by Delimiter" = Table.SplitColumn(FilteredRows, "Order", Splitter.SplitTextByEachDelimiter({"-"}, QuoteStyle.Csv, false), {"Order", "To Delete"}),
    #"Select Columns" = Table.SelectColumns(#"Split Column by Delimiter",{"Order", "Client", "KVA and KV", "Type", "Order Date", "Qty", "PO Item #", "Duplicate", "Engineering Required", "Initial Promised Date", "Tanking Date"}),
        // Get the earliest "Tanking Date" per Order
    #"Groupe Table Tanking Date" = Table.Group(#"Select Columns", "Order", {"Tanking Date", each List.Min([Tanking Date])}),

    // Merge back to get other columns
    #"Merge Tanking Date" = Table.NestedJoin(#"Groupe Table Tanking Date", {"Order"}, #"Select Columns", {"Order"}, "UpdatedTable", JoinKind.LeftOuter),
    #"Expanded UpdatedTable" = Table.ExpandTableColumn(#"Merge Tanking Date", "UpdatedTable", {"Client", "KVA and KV", "Type", "Order Date", "Qty", "Duplicate", "Engineering Required", "Initial Promised Date", "Client Desired Date"}, {"Client", "KVA and KV", "Type", "Order Date", "Qty", "Duplicate", "Engineering Required", "Initial Promised Date", "Client Desired Date"}),

    // Group to find the first available "PO Item #"
    #"Groupe Table PO Item" = Table.Group(#"Select Columns", "Order", {"PO Item #", each List.First(List.RemoveNulls([#"PO Item #"]))}),

    // Merge back with "Groupe Table Tanking Date" instead to keep "Tanking Date"
    #"Merge PO Item" = Table.NestedJoin(#"Groupe Table PO Item", {"Order"}, #"Expanded UpdatedTable", {"Order"}, "UpdatedTable", JoinKind.LeftOuter),
    #"Expanded PO Item Table" = Table.ExpandTableColumn(#"Merge PO Item", "UpdatedTable", {"Tanking Date", "Client", "KVA and KV", "Type", "Order Date", "Qty", "Duplicate", "Engineering Required", "Initial Promised Date", "Client Desired Date"}, {"Tanking Date", "Client", "KVA and KV", "Type", "Order Date", "Qty", "Duplicate", "Engineering Required", "Initial Promised Date", "Client Desired Date"}),
    
    #"Removed Duplicates" = Table.Distinct(#"Expanded PO Item Table", {"Order"}),
    
    #"SourceArchive" = ImportFromIndex("Archive active", "TableArchiveFRM13"),
    #"Changed Type" = Table.TransformColumnTypes(#"SourceArchive",{{"Order", type text}}),
    #"Merge with active archive" = Table.NestedJoin(#"Removed Duplicates", "Order", #"Changed Type", "Order", "Archive",JoinKind.LeftOuter),
    #"Expanded Archive" = Table.ExpandTableColumn(#"Merge with active archive", "Archive", {"Job State"}, {"Job State"}),
    #"Remove Finished Orders" = Table.SelectRows(
        #"Expanded Archive", 
        each Record.Field(_, "Job State") <> "Annuler" and Record.Field(_, "Job State") <> "Terminé"
    ),
    #"Remove Expanded Column" = Table.RemoveColumns(
        #"Remove Finished Orders", 
        {"Job State"}
    ),
    
    #"Added Stack Core Column" = Table.AddColumn(#"Remove Expanded Column", "Stack Core", each if List.Contains(StackList[StackList], [Type]) then "STACK" else "NON"),
    #"Added Promised Date of DWG Column" = Table.AddColumn(#"Added Stack Core Column", "Promised Date of DWG Issue", each Date.AddDays([Order Date],DWG_Promissed_Date_Interval)),
    #"Merged Queries" = Table.NestedJoin(#"Added Promised Date of DWG Column", {"Order"}, TableFournisseursCuve, {"NUMÉRO DE CUVE"}, "TableFournisseursCuve", JoinKind.LeftOuter),
    #"Expanded TableFournisseursCuve" = Table.ExpandTableColumn(#"Merged Queries", "TableFournisseursCuve", {"Fournisseur CUVE"}, {"Fournisseur CUVE"}),
    #"Merged LeedTime" = Table.NestedJoin(#"Expanded TableFournisseursCuve", {"Client"}, LeedTime, {"CLIENT"}, "LeedTime", JoinKind.LeftOuter),
    #"Expanded LeedTime" = Table.ExpandTableColumn(#"Merged LeedTime", "LeedTime", {"Lead time"}, {"Lead time"}),
    LeedTimeReplacementValue = Record.Field(Table.First(Table.SelectRows(LeedTime, each [CLIENT] = "GENERIC VALUE")), "Lead time"),
    #"Replace LeedTime Null" = Table.ReplaceValue(#"Expanded LeedTime", null, LeedTimeReplacementValue, Replacer.ReplaceValue, {"Lead time"}),
    #"Merged ManuelDataUpdate" = Table.NestedJoin(#"Replace LeedTime Null", {"Order"}, ManualDataUpdate, {"Order"}, "ManualDataUpdate", JoinKind.FullOuter),
    #"Expanded ManualDataUpdate" = Table.ExpandTableColumn(#"Merged ManuelDataUpdate", "ManualDataUpdate", {"Designer O", "Designer F", "Special Promised date (date or code)", "Prelim. DWG Progr.", "DWG Intern. Verif.", "Prelim. DWG Issued (date)", "Client Comments Due Date (date)", "Need to Resub. DWG?", "General Arrang. DWG Approved (date)", "Fab. DWG Progr.", "DWG Intern. Verif. 2", "Fab. DWG Issued (date)", "TQC Progress", "Comments", "Root Cause", "Action Plan", "Job State"}, {"Designer O", "Designer F", "Special Promised date (date or code)", "Prelim. DWG Progr.", "DWG Intern. Verif.", "Prelim. DWG Issued (date)", "Client Comments Due Date (date)", "Need to Resub. DWG?", "General Arrang. DWG Approved (date)", "Fab. DWG Progr.", "DWG Intern. Verif. 2", "Fab. DWG Issued (date)", "TQC Progress", "Comments", "Root Cause", "Action Plan", "Job State"}),
    #"Replaced Value" = Table.ReplaceValue(#"Expanded ManualDataUpdate","",0,Replacer.ReplaceValue,{"DWG Intern. Verif. 2"}),
    #"Replaced Value1" = Table.ReplaceValue(#"Replaced Value",null,0,Replacer.ReplaceValue,{"DWG Intern. Verif. 2"}),
    #"Replaced Value2" = Table.ReplaceValue(#"Replaced Value1","","-",Replacer.ReplaceValue,{"Fab. DWG Progr."}),
    #"Replaced Value3" = Table.ReplaceValue(#"Replaced Value2",null,"-",Replacer.ReplaceValue,{"Fab. DWG Progr."}),
    #"Replaced Value4" = Table.ReplaceValue(#"Replaced Value3","","-",Replacer.ReplaceValue,{"Need to Resub. DWG?"}),
    #"Replaced Value5" = Table.ReplaceValue(#"Replaced Value4",null,"-",Replacer.ReplaceValue,{"Need to Resub. DWG?"}),
    #"Replaced Value6" = Table.ReplaceValue(#"Replaced Value5","",0,Replacer.ReplaceValue,{"DWG Intern. Verif."}),
    #"Replaced Value7" = Table.ReplaceValue(#"Replaced Value6",null,0,Replacer.ReplaceValue,{"DWG Intern. Verif."}),
    #"Replaced Value8" = Table.ReplaceValue(#"Replaced Value7","","-",Replacer.ReplaceValue,{"Prelim. DWG Progr."}),
    #"Replaced Value9" = Table.ReplaceValue(#"Replaced Value8",null,"-",Replacer.ReplaceValue,{"Prelim. DWG Progr."}),
    #"Replaced Value10" = Table.ReplaceValue(#"Replaced Value9","","-",Replacer.ReplaceValue,{"TQC Progress"}),
    #"Replaced Value11" = Table.ReplaceValue(#"Replaced Value10",null,"-",Replacer.ReplaceValue,{"TQC Progress"}),
    #"Merged Queries1" = Table.NestedJoin(#"Replaced Value11", {"Order"}, #"TableArchiveFRM10-12", {"Order"}, "TableArchiveFRM10-12", JoinKind.LeftOuter),
    #"Expanded TableArchiveFRM10-12" = Table.ExpandTableColumn(#"Merged Queries1", "TableArchiveFRM10-12", {"Location"}, {"Location"}),
    #"Changed Type1" = Table.TransformColumnTypes(#"Expanded TableArchiveFRM10-12",{{"PO Item #", type text}}),
    #"Merged Queries2" = Table.NestedJoin(#"Changed Type1", {"PO Item #"}, Models, {"ModelName"}, "Models", JoinKind.LeftOuter),
    #"Expanded Models" = Table.ExpandTableColumn(#"Merged Queries2", "Models", {"ModificationStatus"}, {"temp.ModificationStatus"}),
    #"Create Modification Status" = 
        Table.AddColumn(
            #"Expanded Models",
            "Model Status",
            each
                if Text.StartsWith(Text.Upper([#"Order"]), "E")
                then "ETS"
                else if Text.Contains(Text.Upper([#"Order"]),"W")
                then "Warranty"
                else if Text.Contains(Text.Upper([#"Order"]), "R")
                then "Repair"
                else if Text.Contains(Text.Upper([#"Order"]), "P")
                then "Prototype"
                else if [#"temp.ModificationStatus"] <> null and [#"temp.ModificationStatus"] <> ""
                then [#"temp.ModificationStatus"]
                else "New"
        ),
    #"Non Formula Column Names" = List.Intersect({Table.ColumnNames(#"ManualDataUpdate"), Table.ColumnNames(#"Create Modification Status")}),
    #"Reordered To Back To Origin" = Table.ReorderColumns(#"Create Modification Status", #"Non Formula Column Names"),
    #"Changed Date Types" = Table.TransformColumnTypes(#"Reordered To Back To Origin",{{"Order Date", type date}, {"Client Desired Date", type text}, {"Initial Promised Date", type date}, {"Promised Date of DWG Issue", type date}, {"PO Item #", type text}, {"Tanking Date", type date}}),
    #"Reordered Columns" = Table.ReorderColumns(#"Changed Date Types",{"Order", "Qty", "PO Item #", "Model Status", "KVA and KV", "Type", "Client", "Order Date", "Duplicate", "Engineering Required", "Stack Core", "Designer O", "Designer F", "Promised Date of DWG Issue", "Special Promised date (date or code)", "Prelim. DWG Progr.", "DWG Intern. Verif.", "Prelim. DWG Issued (date)", "Client Comments Due Date (date)", "Need to Resub. DWG?", "General Arrang. DWG Approved (date)", "Fab. DWG Progr.", "DWG Intern. Verif. 2", "Fab. DWG Issued (date)", "TQC Progress", "Initial Promised Date", "Client Desired Date", "Tanking Date", "Fournisseur CUVE", "Comments", "Root Cause", "Action Plan", "Lead time", "Location", "Job State", "temp.ModificationStatus"}),
    #"Removed Columns" = Table.RemoveColumns(#"Reordered Columns",{"Lead time"}),
    #"Removed Duplicates1" = Table.Distinct(#"Removed Columns", {"Order"}),
    #"Filtered Rows" = Table.SelectRows(#"Removed Duplicates1", each [Order] <> null and [Order] <> ""),
    #"Removed Columns1" = Table.RemoveColumns(#"Filtered Rows",{"temp.ModificationStatus"})
in
    #"Removed Columns1"