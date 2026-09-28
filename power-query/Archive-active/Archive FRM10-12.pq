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
// with an explicit Table.TransformColumnTypes. `datetext`/`numtext` columns load as text on
// purpose (their history holds non-dates / non-numbers that a real type would turn into
// errors); dates in them are written ISO yyyy-MM-dd, which the refresher's step 8 converts.
// A value that cannot take its declared real type becomes a cell ERROR naming the column,
// never a silent null. The map's real types were chosen where every archived value converts
// (check_frm1012_map.py --base), so only a SharePoint type change could raise one.
let
    Map = Table.Buffer(Table.Sort(ArchiveFrm1012Map, {{"Position", Order.Ascending}})),
    MapRows = Table.ToRecords(Map),
    Pinned = Map[TargetColumn],

    Source = ArchiveFrm1012Source,
    Accumulated = AccumulateIntoLocal(Source, "TableArchiveFRM10_12", "Order"),

    // --- D2 backfill for rows SharePoint no longer sends ---
    // ArchiveFrm1012Source already applied the BO rule to every unit still on SharePoint. The
    // rows AccumulateIntoLocal kept from the local table (units deleted from Order Items: 830
    // of TableArchiveBO's 1,955 rows, 1,032 of its 1,391 non-blank values) never passed
    // through it, so their BO detail would stay null and their blank BO unfilled. Same order
    // for them, minus the Order Items value they no longer have: TableArchiveBO's value if
    // non-blank, else the archive's existing value.
    BOColumns = Table.SelectRows(Map, each [Rule] = "bo")[TargetColumn],
    IsBlank = (v as any) as logical => v = null or v = false or (v is text and Text.Trim(v) = ""),
    SentKeys = Table.Buffer(Table.RenameColumns(Table.SelectColumns(Source, {"Order"}), {{"Order", "__SentOrder"}})),
    WithLocalBO = Table.NestedJoin(Accumulated, {"Order"}, Table.PrefixColumns(ArchiveLocalBO, "__BO"), {"__BO.Order"}, "__BO", JoinKind.LeftOuter),
    WithSent = Table.NestedJoin(WithLocalBO, {"Order"}, SentKeys, {"__SentOrder"}, "__Sent", JoinKind.LeftOuter),
    Flagged = Table.AddColumn(
        Table.AddColumn(WithSent, "__IsSent", each not Table.IsEmpty([__Sent]), type logical),
        "__BORow", each if Table.IsEmpty([__BO]) then null else [__BO]{0}),
    Backfilled = List.Accumulate(
        BOColumns,
        Flagged,
        (t, c) => Table.ReplaceValue(
            t,
            each Record.Field(_, c),
            each
                let
                    cur = Record.Field(_, c),
                    arc = if [__BORow] = null then null else Record.Field([__BORow], "__BO." & c)
                in
                    if [__IsSent] then cur                 // already ruled in ArchiveFrm1012Source
                    else if not IsBlank(arc) then arc
                    else if cur <> null then cur
                    else arc,                              // keeps a TableArchiveBO false over null
            Replacer.ReplaceValue,
            {c})),
    BackfillDone = Table.RemoveColumns(Backfilled, {"__BO", "__Sent", "__IsSent", "__BORow"}),

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
    Iso = (d as date) as text =>
        Text.From(Date.Year(d)) & "-" & Text.PadStart(Text.From(Date.Month(d)), 2, "0")
            & "-" & Text.PadStart(Text.From(Date.Day(d)), 2, "0"),

    Bad = (col as text, want as text, v as any) =>
        error Error.Record("ArchiveFRM10_12.BadValue",
            col & ": cannot store this value as " & want & " (map Type). Fix the source value or the map.",
            [Column = col, Value = v]),

    AsText = (col as text, v as any) as any =>
        if v = null then null
        else if v is text then (if Text.Trim(v) = "" then null else v)
        else if v is number then Number.ToText(v, null, "en-US")
        else if v is logical then (if v then "TRUE" else "FALSE")
        else if v is date then Iso(v)
        else if v is datetime then
            (if DateTime.Time(v) = #time(0, 0, 0) then Iso(DateTime.Date(v))
             else Iso(DateTime.Date(v)) & " " & Time.ToText(DateTime.Time(v), "HH:mm:ss", "en-US"))
        else if v is time then Time.ToText(v, "HH:mm:ss", "en-US")
        else Bad(col, "text", v),

    // A SharePoint datetime ("2026-10-30T04:00:00Z", the calculated EstimatedDeliveryDate)
    // keeps its first 10 characters: the stored local-midnight date, like every date-only.
    AsDateText = (col as text, v as any) as any =>
        if v is datetime then Iso(DateTime.Date(v))
        else if v is datetimezone then Iso(DateTime.Date(DateTimeZone.RemoveZone(v)))
        else if v is text and Text.Length(v) > 10 and Text.Middle(v, 4, 1) = "-" and Text.Middle(v, 10, 1) = "T"
            then Text.Start(v, 10)
        else AsText(col, v),

    AsNumText = (col as text, v as any) as any =>
        if v is number then Number.ToText(v, null, "fr-CA") else AsText(col, v),

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
                     (try (let p = Text.Split(Text.BeforeDelimiter(Text.BeforeDelimiter(t, "T"), " "), "-") in #date(Number.From(p{0}), Number.From(p{1}), Number.From(p{2})))
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
        else type text,     // text, datetext, numtext

    Normalised = Table.TransformColumns(PinChecked, List.Transform(MapRows, each {[TargetColumn], Converter(_), MType([Type])})),

    // --- declare the types (the Data Model takes these, not `any`) ---
    Typed = Table.TransformColumnTypes(Normalised, List.Transform(MapRows, each {[TargetColumn], MType([Type])}))
in
    Typed
