// Query: Archive FRM10-12
//
// TableArchiveFRM10_12, read from SharePoint directly (plan D1: the FRM10-12 viewer is
// skipped for archiving). Replaces the old TrackRemoteTable("FRM10-12", "TableOrders", ...)
// formula IN PLACE: same query name, same load, same table (the Nightly Sync reads it by
// id {17014A43-...}). Never recreate the table.
//
//   ArchiveTyped (A) -> ArchiveFrm1012Joined -> ArchiveFrm1012Source (built by
//   ArchiveFrm1012Map) -> AccumulateIntoLocal -> PIN to the map's 111 columns -> TYPE
//
// LOUD, never silent (review C): the local archive unreadable, a row dropped by
// AccumulateIntoLocal's Table.Distinct, or any cell error each FAIL the refresh, which leaves
// the table as it was. See the guards after `Source` and at the end.
//
// PINNED SHAPE. AccumulateIntoLocal is schema-adaptive (it appends any column it has not
// seen); this table must not be. After accumulating, exactly the map's TargetColumns are
// selected in map order, and a missing one is an ERROR, never a null column. The 111 are
// the 93 columns of the 2026-09-27 23:56 archive, then TableArchiveBO's 18 BO detail
// columns (D2, the one approved addition).
//
// D4: no "already archived" self-filter. Units keep updating while they are on SharePoint;
// once deleted there, AccumulateIntoLocal keeps their last row forever.
//
// ---------------------------------------------------------------------------------------
// BO (D2): the backfill and why it survives TableArchiveBO's removal
//
// Per cell, for `BO` and the 18 BO detail columns, the FIRST NON-BLANK of:
//   1. the unit's Order Items field (the ongoing truth, non-blank always wins)
//   2. TableArchiveBO's same-named column (history; ArchiveLocalBO, empty once removed)
//   3. this archive's own previous value for the unit (ArchiveFrm1012Previous)
// Blank = null, "", whitespace, or false.
//
// Why 3 exists: AccumulateIntoLocal REPLACES a unit's whole row while SharePoint still sends
// it. Without 3, a unit still on the list whose Order Items BO fields are blank would keep
// its TableArchiveBO value only while that table exists; the first refresh after removal
// would overwrite it with blank. With 3, a value once archived is carried forward, so
// removal loses nothing (check_archive_rebuild.py proves this on the copy: refresh, remove
// TableArchiveBO, refresh again, compare).
// Rows SharePoint no longer sends (kept by AccumulateIntoLocal) get the same rule after
// accumulating, minus source 1: TableArchiveBO's value if non-blank, else their existing value
// (step "D2 backfill for rows SharePoint no longer sends"). Most of TableArchiveBO's history is
// on such rows, so without that step it would never reach the archive. Once filled, the value
// is the row's own and survives TableArchiveBO's removal.
// ⚠️ The cost, accepted: clearing a BO field on SharePoint does not clear the archive; the
// archive keeps the last non-blank value. A different non-blank value does replace it.
// Conflicts (1 and 2 both non-blank and different) are listed by ArchiveBOConflicts.
//
// `legacy` columns (Duplicate, Duplicate Order, 83-92) always take 3: they are never on
// SharePoint, so old rows keep their values and new rows get null.
//
// ---------------------------------------------------------------------------------------
// TYPES. The table loads through the Data Model, and Table.Combine with the local table
// makes every column `any`, which the Data Model loads as TEXT (the 09-27 text-dates
// incident). So the last steps normalise every value to its map Type and then declare it
// with an explicit Table.TransformColumnTypes. Since 2026-09-28 the table is loaded straight
// to the SHEET (option 2; the Data Model rejected this query and gave nothing back), so
// `text`/`datetext`/`numtext` columns are type `any` and keep each cell's native value: a real
// date or number where the value is one, the placeholder text ("EC", ".", "TBD") where not.
// The refresher's step 8 no longer has anything to convert here; it stays as a safety net.
// A value that cannot take its declared real type becomes a cell ERROR naming the column,
// never a silent null. The map's real types were chosen where every archived value converts
// (check_frm1012_map.py --base), so only a SharePoint type change could raise one.
let
    Map = Table.Buffer(Table.Sort(ArchiveFrm1012Map, {{"Position", Order.Ascending}})),
    MapRows = Table.ToRecords(Map),
    Pinned = Map[TargetColumn],

    Source = ArchiveFrm1012Source,
    LocalName = ArchiveFrm1012LocalName,   // "TableArchiveFRM10_12", or its seed during the one-time switch to a sheet load

    // --- guards around AccumulateIntoLocal (review C, 2026-09-28) ---
    // 1. The archive must be READABLE. AccumulateIntoLocal reads it inside `try ... otherwise
    //    null`, so a failed read (privacy/firewall error, renamed table) would silently rebuild
    //    the archive from SharePoint alone and drop every unit already deleted there, which is
    //    exactly what the Nightly Sync's gate looks for. This table is never recreated, so it
    //    is read here first, without `try`: a failure fails the refresh.
    Local = if List.Contains(Excel.CurrentWorkbook()[Name], LocalName)
            then Excel.CurrentWorkbook(){[Name = LocalName]}[Content]
            else error Error.Record("ArchiveFRM10_12.NoLocalTable",
                     LocalName & " not found in this workbook: refusing to rebuild the archive from SharePoint alone."),
    LocalKeys = List.Buffer(List.Transform(Table.Column(Local, "Order"), each if _ = null then null else Text.From(_, "en-US"))),
    SentKeyList = List.Buffer(Table.Column(Source, "Order")),
    // 2. No row may be DROPPED. AccumulateIntoLocal ends in Table.Distinct on Order, which drops
    //    rows silently (two blank-Order rows collapse into one; a hand-made duplicate vanishes).
    //    Expected = every unit SharePoint sends + every local row whose Order it no longer sends.
    Expected = List.Count(SentKeyList) + List.Count(List.RemoveItems(LocalKeys, SentKeyList)),
    Accumulated0 = Table.Buffer(AccumulateIntoLocal(Source, LocalName, "Order")),
    Accumulated =
        if Table.RowCount(Accumulated0) = Expected then Accumulated0
        else error Error.Record("ArchiveFRM10_12.RowsDropped",
            LocalName & ": expected " & Text.From(Expected) & " rows (SharePoint " & Text.From(List.Count(SentKeyList))
                & " + kept " & Text.From(Expected - List.Count(SentKeyList)) & "), got " & Text.From(Table.RowCount(Accumulated0))
                & ". A duplicate or blank Order in the archive collapsed in AccumulateIntoLocal's Table.Distinct.",
            [Expected = Expected, Got = Table.RowCount(Accumulated0)]),

    // --- D2 backfill for rows SharePoint no longer sends ---
    // ArchiveFrm1012Source already applied the BO rule to every unit still on SharePoint. The
    // rows AccumulateIntoLocal kept from the local table (units deleted from Order Items: 830
    // of TableArchiveBO's 1,955 rows, 1,032 of its 1,391 non-blank values) never passed
    // through it, so their BO detail would stay null and their blank BO unfilled. Same order
    // for them, minus the Order Items value they no longer have: TableArchiveBO's value if
    // non-blank, else the archive's existing value.
    BOColumns = Table.SelectRows(Map, each [Rule] = "bo")[TargetColumn],
    IsBlank = (v as any) as logical => v = null or v = false or (v is text and Text.Trim(v) = ""),
    // Performance (2026-09-28, first real evaluation ~126 s): this used to be two
    // Table.NestedJoin + 19 chained Table.ReplaceValue passes that read the nested tables per row.
    // A nested-join table read row by row is a lazy filter of the right-hand table, so every pass
    // re-scanned it. Now it's ONE pass with record "dictionaries" (O(1) field lookup): the sent keys
    // and TableArchiveBO keyed by Order. Both key sets are unique (ArchiveFrm1012Joined and
    // ArchiveLocalTable error on duplicates), which Record.FromList requires.
    // Same rule per BO column for a row SharePoint no longer sends:
    //   TableArchiveBO's value if non-blank, else the row's own value if not null, else
    //   TableArchiveBO's (a TableArchiveBO false beats null).
    // Rows SharePoint still sends were already ruled in ArchiveFrm1012Source, so they pass through
    // untouched. So do rows TableArchiveBO does not know.
    SentSet = Record.FromList(List.Repeat({true}, List.Count(SentKeyList)), SentKeyList),
    BOByOrder = Record.FromList(Table.ToRecords(ArchiveLocalBO), Table.Column(ArchiveLocalBO, "Order")),
    FillRow = (r as record) as record =>
        let
            k = r[Order],
            bo = if k = null or Record.HasFields(SentSet, k) then null else Record.FieldOrDefault(BOByOrder, k, null)
        in
            if bo = null then r
            else r & Record.FromList(
                List.Transform(BOColumns, (c) =>
                    let cur = Record.Field(r, c), arc = Record.Field(bo, c)
                    in  if not IsBlank(arc) then arc else if cur <> null then cur else arc),
                BOColumns),
    BackfillDone = Table.FromRecords(Table.TransformRows(Accumulated, FillRow), Table.ColumnNames(Accumulated)),

    // --- pin ---
    Missing = List.Difference(Pinned, Table.ColumnNames(BackfillDone)),
    PinChecked =
        if List.IsEmpty(Missing) then Table.SelectColumns(BackfillDone, Pinned)
        else error Error.Record(
            "ArchiveFRM10_12.MissingPinnedColumns",
            "TableArchiveFRM10_12 must have exactly the " & Text.From(List.Count(Pinned))
                & " pinned columns of ArchiveFrm1012Map; missing: " & Text.Combine(Missing, ", "),
            [Missing = Missing]),

    // --- normalise values to the map Type ---
    Iso = (d as date) as text => Date.ToText(d, [Format = "yyyy-MM-dd", Culture = "en-US"]),

    Bad = (col as text, want as text, v as any) =>
        error Error.Record("ArchiveFRM10_12.BadValue",
            col & ": cannot store this value as " & want & " (map Type). Fix the source value or the map.",
            [Column = col, Value = v]),

    // Sheet load (2026-09-28, option 2): a sheet-loaded column may hold a different type per
    // cell, so "text"/"datetext"/"numtext" columns keep each cell's NATIVE value instead of
    // forcing everything to text (the Data Model needed one type per column; that detour is
    // gone). History rows are therefore left exactly as they were: a number stays a number,
    // TRUE/FALSE stays logical, a placeholder ("EC", ".", "TBD", "2025-99-99") stays text.
    AsText = (col as text, v as any) as any =>
        if v = null then null
        else if v is text then (if Text.Trim(v) = "" then null else v)
        else if v is number or v is logical or v is date then v
        else if v is datetime then
            (if DateTime.Time(v) = #time(0, 0, 0) then DateTime.Date(v) else v)
        else if v is time then v
        else Bad(col, "text", v),

    // A real date wherever the value IS a date (date, datetime, a SharePoint ISO datetime such as
    // "2026-10-30T04:00:00Z" -> its first 10 characters, ISO or US date text); anything else
    // (placeholders, "pickup 2025-01-06", impossible dates like 2025-99-99) is kept as it is.
    AsDateText = (col as text, v as any) as any =>
        if v is date then v
        else if v is datetime then DateTime.Date(v)
        else if v is datetimezone then DateTime.Date(DateTimeZone.RemoveZone(v))
        else if v is text then
            (let t = Text.Trim(v),
                 rest = if Text.Length(t) > 10 then Text.Trim(Text.Range(t, 10)) else "",
                 // after the date only a TIME may follow ("T04:00:00Z", " 12:00:00 AM"); any other
                 // text ("2025-07-22 (estimé)") means the cell is a note, and it is kept as written
                 restIsTime = rest = "" or Text.StartsWith(rest, "T")
                              or (try (Time.FromText(rest, "en-US") is time) otherwise false),
                 iso = if Text.Length(t) >= 10 and Text.Middle(t, 4, 1) = "-" and Text.Middle(t, 7, 1) = "-" and restIsTime
                       then (try #date(Number.FromText(Text.Start(t, 4), "en-US"), Number.FromText(Text.Middle(t, 5, 2), "en-US"),
                                       Number.FromText(Text.Middle(t, 8, 2), "en-US")) otherwise null)
                       else null,
                 us = if iso = null and Text.Contains(t, "/")
                      then (try DateTime.Date(DateTime.FromText(t, "en-US")) otherwise null)
                      else null
             in  if t = "" then null else if iso <> null then iso else if us <> null then us else v)
        else AsText(col, v),

    // A number wherever the value IS a number (native, or text like "33,625" / "24.9");
    // anything else ("24.9 kV", "100-104", "Inconnu") is kept as it is.
    AsNumText = (col as text, v as any) as any =>
        if v is number then v
        else if v is text then
            (let t = Text.Trim(v),
                 n = if t = "" then null else (try Number.FromText(Text.Replace(t, ",", "."), "en-US") otherwise null)
             in  if t = "" then null else if n <> null then n else v)
        else AsText(col, v),

    AsNumber = (col as text, v as any) as any =>
        if v = null then null
        else if v is number then v
        else if v is text then
            (if Text.Trim(v) = "" then null
             else try Number.FromText(Text.Replace(Text.Trim(v), ",", "."), "en-US") otherwise Bad(col, "number", v))
        else Bad(col, "number", v),

    AsDate = (col as text, v as any) as any =>
        if v = null then null
        else if v is date then v
        else if v is datetime then DateTime.Date(v)
        else if v is datetimezone then DateTime.Date(DateTimeZone.RemoveZone(v))
        else if v is number then Date.From(v)            // an Excel serial (General-formatted cell)
        else if v is text then
            (let t = Text.Trim(v)
             in  if t = "" then null
                 else if Text.Middle(t, 4, 1) = "-" then
                     (try (let p = Text.Split(Text.BeforeDelimiter(Text.BeforeDelimiter(t, "T"), " "), "-") in #date(Number.FromText(p{0}, "en-US"), Number.FromText(p{1}, "en-US"), Number.FromText(p{2}, "en-US")))
                      otherwise Bad(col, "date", v))
                 else (try DateTime.Date(DateTime.FromText(t, "en-US")) otherwise Bad(col, "date", v)))   // "9/24/2026 12:00:00 AM"
        else Bad(col, "date", v),

    AsLogical = (col as text, v as any) as any =>
        if v = null then null
        else if v is logical then v
        else if v is text then
            (if Text.Trim(v) = "" then null
             else if Text.Upper(Text.Trim(v)) = "TRUE" then true
             else if Text.Upper(Text.Trim(v)) = "FALSE" then false
             else Bad(col, "logical", v))
        else Bad(col, "logical", v),

    Converter = (m as record) as function =>
        let col = m[TargetColumn], t = m[Type] in
            if t = "text" then (v) => AsText(col, v)
            else if t = "datetext" then (v) => AsDateText(col, v)
            else if t = "numtext" then (v) => AsNumText(col, v)
            else if t = "number" then (v) => AsNumber(col, v)
            else if t = "date" then (v) => AsDate(col, v)
            else if t = "logical" then (v) => AsLogical(col, v)
            else error Error.Record("ArchiveFRM10_12.UnknownType", "Unknown map Type """ & t & """ for " & col, m),

    MType = (t as text) as type =>
        if t = "number" then type number
        else if t = "date" then type date
        else if t = "logical" then type logical
        else type any,      // text, datetext, numtext: native value per cell (sheet load, 2026-09-28)

    Normalised = Table.TransformColumns(PinChecked, List.Transform(MapRows, each {[TargetColumn], Converter(_), MType([Type])})),

    // --- declare the types (real types where the map says so; `any` for the mixed columns) ---
    // Values are already converted above, so the culture only makes the step culture-free
    // on paper (the workbook runs fr-CA).
    // Buffered once. The guards below read it, and so does the load. The Data Model load may
    // evaluate the query more than once, so this keeps the checks from re-running everything
    // upstream. If Table.Buffer ever raises on a cell error instead of keeping it, that is the
    // same BadValue message, still loud.
    Typed = Table.Buffer(Table.TransformColumnTypes(Normalised, List.Transform(MapRows, each {[TargetColumn], MType([Type])}), "en-US")),

    // --- a cell error fails the refresh (review C) ---
    // Excel loads a cell-level error as an EMPTY cell and still reports success, so the
    // BadValue errors above would reach the Nightly Sync as silent blanks. Same rule as
    // ArchiveList: any cell error fails the whole refresh, naming the first bad unit, column
    // and message; the table keeps its previous contents.
    ErrRows = Table.SelectRowsWithErrors(Typed),

    // --- only primitive values reach the Data Model (2026-09-28) ---
    // The Data Model load failed once with "Column '134217730' is too large for this instance
    // of Analysis Services". Each column may hold only null / text / number / date / logical,
    // with text short enough for an Excel cell (32,767 chars; the table is shown on a sheet).
    // Anything else (a list, record, table, binary, function, datetime, datetimezone, time)
    // fails the refresh, naming the column, the first Order and the value's kind. Runs only
    // once the table has no cell errors, because reading an error cell would raise it.
    KindOf = (v as any) as text =>
        if v is list then "list" else if v is record then "record" else if v is table then "table"
        else if v is binary then "binary" else if v is function then "function"
        else if v is datetimezone then "datetimezone" else if v is datetime then "datetime"
        else if v is time then "time" else if v is duration then "duration" else "other",
    MaxText = 32767,
    IsPrimitive = (v as any) as logical =>
        v = null or v is number or v is logical or (v is date and not (v is datetime))
        or (v is text and Text.Length(v) <= MaxText),
    PrimCheck = (t as table) as table =>
        let
            BadCol = List.First(List.Select(Table.ColumnNames(t), (c) => not List.AllTrue(List.Transform(Table.Column(t, c), IsPrimitive))), null),
            Detail = if BadCol = null then null else
                let
                    rows = Table.SelectRows(t, (r) => not IsPrimitive(Record.Field(r, BadCol))),
                    v = Record.Field(rows{0}, BadCol),
                    kind = if v is text then "text of " & Text.From(Text.Length(v), "en-US") & " chars" else KindOf(v)
                in
                    [Order = rows{0}[Order], Kind = kind, Count = Table.RowCount(rows)]
        in
            if BadCol = null then t
            else error Error.Record("ArchiveFRM10_12.NonPrimitive",
                LocalName & ": column " & BadCol & " holds " & Text.From(Detail[Count], "en-US") & " non-primitive value(s); first Order "
                    & (try Text.From(Detail[Order], "en-US") otherwise "?") & " (" & Detail[Kind] & "). Only null/text/number/date/logical may reach the Data Model.",
                [Column = BadCol, Order = Detail[Order], Kind = Detail[Kind]]),

    Out =
        if Table.IsEmpty(ErrRows) then PrimCheck(Typed)
        else
            let
                First = Table.First(ErrRows),
                BadCols = List.Select(Table.ColumnNames(ErrRows), (c) => (try Record.Field(First, c))[HasError]),
                Probe = if List.IsEmpty(BadCols) then null else try Record.Field(First, BadCols{0}),
                MsgText = if Probe <> null and Probe[HasError] then Probe[Error][Message] else "?",
                OrderTxt = try Text.From(Record.Field(First, "Order"), "en-US") otherwise "?"
            in
                error Error.Record("ArchiveFRM10_12.CellErrors",
                    LocalName & ": " & Text.From(Table.RowCount(ErrRows)) & " row(s) with cell errors; first Order "
                        & OrderTxt & ", column(s) " & Text.Combine(List.FirstN(BadCols, 10), ", ") & ": " & MsgText)
in
    Out
