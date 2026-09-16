// Query: AccumulateIntoLocal
//
// The archive's accumulate step, lifted verbatim out of TrackRemoteTable so a second
// kind of source can reuse it instead of copying 20 lines of subtle merge logic.
//
// Given a freshly-read source table and the name of a local archive table, return the
// union of:
//    - local rows whose key is NOT in the source   (they have left the live system:
//      this is what makes it an ARCHIVE rather than a mirror)
//    - every source row, stamped with today's sync date
//
// 🔑 IT IS SCHEMA-ADAPTIVE, and that is the property that matters most here. Columns
// present in the source but not in the archive are ADDED; columns the source has since
// dropped are RETAINED as nulls. So an archive built this way never needs its column
// list maintained by hand -- which is exactly how `Archive FRM10-12` came to be missing
// 22 `Order Items` columns. It was not a limitation of this function; nothing was
// pointed at the list.
//
// ⚠️ PrimaryKey must be 100% populated AND 100% distinct in BOTH tables. The final
// Table.Distinct drops duplicate keys SILENTLY -- no error, just fewer archived rows --
// and a null key cannot match in the anti-join, so such a row is kept forever and
// re-added on every refresh. See docs/archive-cover-all-lists-2026-09-16.md for the
// measured per-list key choices.
let
    AccumulateIntoLocal = (SourceTable as table, LocalTable as text, PrimaryKey as text) as table =>
    let
        UpdateDateColName = "Last Synchronisation Date",
        Today = DateTime.Date(DateTime.LocalNow()),
        #"Change PK Type Remote" = Table.TransformColumnTypes(SourceTable, {{PrimaryKey, type text}}),
        #"Remote Columns" = Table.ColumnNames(#"Change PK Type Remote"),
        #"Local Source Exists" = try Excel.CurrentWorkbook(){[Name=LocalTable]}[Content] otherwise null,
        #"Local Source Raw" = if #"Local Source Exists" <> null then #"Local Source Exists" else #table(#"Remote Columns", {}),
        #"Local Source" = if Table.HasColumns(#"Local Source Raw", UpdateDateColName) then #"Local Source Raw" else Table.AddColumn(#"Local Source Raw", UpdateDateColName, each Today, type date),
        #"Change PK Type Local" = Table.TransformColumnTypes(#"Local Source", {{PrimaryKey, type text}}),
        #"Local Columns" = Table.ColumnNames(#"Change PK Type Local"),
        #"Removed Remote Columns" = List.Difference(#"Local Columns", #"Remote Columns"),
        #"Added Remote Columns" = List.Difference(#"Remote Columns", #"Local Columns"),
        #"Added Removed Columns to Remote" = AddMultipleNullColumns(#"Change PK Type Remote", #"Removed Remote Columns"),
        #"Added New Columns to Local" = AddMultipleNullColumns(#"Change PK Type Local", #"Added Remote Columns"),
        #"Columns Order" = List.Combine({#"Remote Columns", #"Removed Remote Columns"}),
        #"Reordered Remote Source" = Table.ReorderColumns(#"Added Removed Columns to Remote", #"Columns Order"),
        #"Reordered Local Source" = Table.ReorderColumns(#"Added New Columns to Local", #"Columns Order"),
        #"Merged Local Source" = Table.NestedJoin(#"Reordered Local Source", {PrimaryKey}, #"Reordered Remote Source", {PrimaryKey}, "TableRemote", JoinKind.LeftAnti),
        #"Removed Columns" = Table.RemoveColumns(#"Merged Local Source", {"TableRemote"}),
        #"Remote Rows with Sync Date" = Table.TransformColumns(#"Reordered Remote Source", {{UpdateDateColName, each Today, type date}}),
        #"Combine Local and Remote" = Table.Combine({#"Removed Columns", #"Remote Rows with Sync Date"}),
        #"Removed Duplicates" = Table.Distinct(#"Combine Local and Remote", PrimaryKey),
        #"Applied Data Format Enforcement" = EnforceFormats(#"Removed Duplicates")
    in
        #"Applied Data Format Enforcement"
in
    AccumulateIntoLocal
