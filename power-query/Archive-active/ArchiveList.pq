// Query: ArchiveList
//
// Archive one of the five main lists into a local table, keyed on the SharePoint item Id.
//   title:      "Order Items" | "Order" | "Models" | "Model Revisions" | "Clients"
//   localTable: the Excel table this query loads to (it reads its own previous output)
//
//   = AccumulateIntoLocal(ArchiveTyped(title), localTable, "Id")   (reused unchanged)
//     + a final Table.TransformColumnTypes built from ArchiveTyped's column types, which come
//       from the live SharePoint catalog.
//
// Why the final typing: AccumulateIntoLocal ends in EnforceFormats, a per-cell
// Table.TransformColumns that drops every column type, and it turns the key into text. Untyped
// values are how the 09-27 text-date incident happened. Here each column reaches Excel typed:
// date-only as date, numbers as number, yes/no as logical, Id as whole number, ISO datetimes
// and JSON as text.
//
// Additive, not a mirror: a row whose Id has left SharePoint is kept with its last state (its
// `Last Synchronisation Date` stops); a new SharePoint column is appended; a column dropped on
// SharePoint is kept with its old values (it has no catalog type, so it keeps Excel's).
//
// LOUD, never silent (AccumulateIntoLocal's Table.Distinct would drop duplicate keys quietly and
// its `try ... otherwise` would treat an unreadable local table as an empty one):
//   - a null or duplicate Id on SharePoint or in the local table  -> error
//   - the local table exists but cannot be read                   -> error (no try here)
//   - the result has fewer rows than remote + local-only rows      -> error
//   - any cell error (Excel would load it as an empty cell)         -> error
//
// Privacy / Formula.Firewall (measured 2026-09-28 on a copy of the 09-27 23:56 archive): the
// workbook has Queries.FastCombine = False (privacy levels NOT ignored), and this machine's
// Power Query GlobalPrivacyLevel setting is 0. Mixing SharePoint REST (ArchiveFetch) with
// Excel.CurrentWorkbook in this one function still refreshed with no firewall error, the same way
// the live TrackRemoteTable mixes Web.Contents with Excel.CurrentWorkbook. Proven, not assumed: a
// fake row (Id 999999) added to TableArchiveOrder survived the next refresh (474 rows), so the
// local table really is read; a duplicate Id 4 added the same way failed the refresh loudly.
// No staging query was needed. If another machine's privacy settings ever raise
// Formula.Firewall here, the error is loud (no try around the local read), never an empty archive.
(title as text, localTable as text) as table =>
let
    Key       = "Id",
    Remote    = ArchiveTyped(title),
    RemoteIds = List.Transform(Table.Column(Remote, Key), each if _ = null then null else Text.From(_)),
    Dupes     = (ids as list) as list => List.Distinct(List.Select(ids, (x) => List.Count(List.Select(ids, each _ = x)) > 1)),
    CheckIds  = (ids as list, where as text) as logical =>
        if List.NonNullCount(ids) <> List.Count(ids)
            then error Error.Record("ArchiveList", where & ": " & Text.From(List.Count(ids) - List.NonNullCount(ids)) & " row(s) with a null Id.")
        else if List.Count(List.Distinct(ids)) <> List.Count(ids)
            then error Error.Record("ArchiveList", where & ": duplicate Id(s) " & Text.Combine(List.FirstN(Dupes(ids), 10), ", ") & ".")
        else true,

    // The local table, read WITHOUT try: if it exists, it must be readable.
    HasLocal  = List.Contains(Excel.CurrentWorkbook()[Name], localTable),
    Local0    = if HasLocal then Excel.CurrentWorkbook(){[Name = localTable]}[Content] else null,
    // First load: a table just created by Apply-ArchivePowerQuery.ps1 is an empty placeholder
    // (one "Column1", no data). Treat it as "no archive yet". A table WITH data but no Id errors below.
    IsPlaceholder = Local0 <> null and not Table.HasColumns(Local0, Key)
                    and List.IsEmpty(List.Select(List.Combine(Table.ToRows(Local0)), each _ <> null and _ <> "")),
    Local     = if IsPlaceholder then null else Local0,
    // AccumulateIntoLocal reads the local table by name itself; for a placeholder, hand it a name
    // that does not exist so it starts from an empty archive.
    AccName   = if IsPlaceholder then localTable & " (first load)" else localTable,
    LocalIds  = if Local = null then {}
                else if not Table.HasColumns(Local, Key)
                    then error Error.Record("ArchiveList", localTable & " has no '" & Key & "' column - not an Id-keyed archive table.")
                else List.Transform(Table.Column(Local, Key), each if _ = null then null else Text.From(_)),

    Checked   = CheckIds(RemoteIds, "SharePoint list '" & title & "'")
                and CheckIds(LocalIds, "local table " & localTable),
    Accumulated = if Checked then AccumulateIntoLocal(Remote, AccName, Key) else null,

    Expected  = List.Count(RemoteIds) + List.Count(List.Difference(LocalIds, RemoteIds)),
    Counted   = if Table.RowCount(Accumulated) = Expected then Accumulated
                else error Error.Record("ArchiveList", localTable & ": expected " & Text.From(Expected)
                         & " rows (SharePoint " & Text.From(List.Count(RemoteIds)) & " + kept "
                         & Text.From(Expected - List.Count(RemoteIds)) & "), got " & Text.From(Table.RowCount(Accumulated)) & "."),

    // Final typing: every column ArchiveTyped typed (i.e. every column SharePoint still has), plus the sync date.
    RemoteType = Value.Type(Remote),
    Types     = List.Transform(Table.ColumnNames(Remote), each {_, Type.TableColumn(RemoteType, _)})
                & {{"Last Synchronisation Date", type date}},
    Typed     = Table.TransformColumnTypes(Counted, Types, "en-US"),

    // Excel loads a cell-level error as an EMPTY cell and still reports success, which would be a
    // silent loss. Any cell error fails the refresh instead, naming the first bad row and columns.
    ErrRows   = Table.SelectRowsWithErrors(Typed),
    Out       = if Table.IsEmpty(ErrRows) then Typed
                else let
                         First = Table.First(ErrRows),
                         Bad   = List.Select(Table.ColumnNames(ErrRows), (c) => (try Record.Field(First, c))[HasError]),
                         IdTxt = try Text.From(Record.Field(First, Key)) otherwise "?"
                     in  error Error.Record("ArchiveList", localTable & ": " & Text.From(Table.RowCount(ErrRows))
                             & " row(s) with cell errors; first Id " & IdTxt & ", column(s) " & Text.Combine(List.FirstN(Bad, 10), ", ") & ".")
in
    Out
