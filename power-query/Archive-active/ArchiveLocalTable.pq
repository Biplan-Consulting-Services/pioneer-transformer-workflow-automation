// Query: ArchiveLocalTable
//
// Reads a table of THIS workbook (Excel.CurrentWorkbook) as {Key, Columns...}, keyed on
// text, for the FRM10-12 adapter's two local inputs:
//   ArchiveLocalBO          TableArchiveBO        (the D2 backfill, until it is removed)
//   ArchiveFrm1012Previous  TableArchiveFRM10_12  (the archive's own previous values)
//
// - The table not existing is NORMAL (TableArchiveBO is removed after one verified cycle;
//   a first build has no archive yet): it returns an empty table with the same columns.
// - A column the table lacks comes back null (MissingField.UseNull). The BO detail columns
//   do not exist in TableArchiveFRM10_12 until its first refresh with them.
// - Rows with a null/"" key are dropped here: they cannot be matched to anything.
// - A DUPLICATE key is an error, never a silent pick (plan, reviewer C: silent drops become
//   loud checks). Both source tables are written by AccumulateIntoLocal, which dedups, so
//   this can only fire if someone edited a table by hand.
let
    ArchiveLocalTable = (TableName as text, Key as text, Columns as list) as table =>
    let
        Wanted = List.Combine({{Key}, List.RemoveItems(Columns, {Key})}),
        Found = try Excel.CurrentWorkbook(){[Name = TableName]}[Content] otherwise null,
        Raw = if Found = null then #table(Wanted, {}) else Found,
        Selected = Table.SelectColumns(Raw, Wanted, MissingField.UseNull),
        Keyed = Table.TransformColumns(Selected, {{Key, each if _ = null then null else Text.From(_), type nullable text}}),
        NonBlank = Table.SelectRows(Keyed, each Record.Field(_, Key) <> null and Record.Field(_, Key) <> ""),
        DupKeys = Table.Column(
            Table.SelectRows(Table.Group(NonBlank, {Key}, {{"n", Table.RowCount, Int64.Type}}), each [n] > 1),
            Key),
        Checked =
            if List.IsEmpty(DupKeys) then Table.Buffer(NonBlank)
            else error Error.Record(
                "ArchiveLocalTable.DuplicateKey",
                TableName & " has " & Text.From(List.Count(DupKeys)) & " duplicate " & Key & " value(s): "
                    & Text.Combine(List.FirstN(DupKeys, 20), ", "),
                [Table = TableName, Key = Key, Duplicates = DupKeys])
    in
        Checked
in
    ArchiveLocalTable
