// E8b - one row per column per mirrored list: the reference to check BEFORE naming a
// field in a script. Names and types come from the platform (_api/v2.0 columns),
// "synced from" from SyncedFrom (generated from the N3 flow definitions), and the
// notes are rules applied by type/name - the traps this repo has already paid for.
let
    Lists     = {"Order Items", "Order", "Models", "Model Revisions", "Clients", "Index", "Models SA"},
    AllLists  = SP_Json("_api/web/lists", [#"$select" = "Id,Title"])[value],
    TitleById = Record.FromList(List.Transform(AllLists, each [Title]),
                                List.Transform(AllLists, each Text.Lower([Id]))),
    Facets    = {"text", "number", "currency", "dateTime", "boolean", "choice", "lookup",
                 "personOrGroup", "hyperlinkOrPicture", "calculated", "geolocation", "term",
                 "thumbnail", "contentApprovalStatus"},

    Row = (listTitle as text, c as record, prof as record) as record =>
        let
            Type   = List.First(List.Select(Facets, (f) => Record.HasFields(c, f)), "other"),
            // E8c: the CSV column that holds this field (lookups/people: their id), its fill rate
            // over the mirrored rows, and whether it can identify a row. `Order.Title` is empty on
            // every row - the order number is Order_x0020_Number1 - and nothing said so.
            ByIdCol = Type = "lookup" or Type = "personOrGroup",
            RestCol = if ByIdCol then c[name] & "Id" else c[name],
            CsvCol  = Record.FieldOrDefault(prof[map], RestCol, null),
            Vals    = if CsvCol = null then null else Table.Column(prof[data], CsvCol),
            Filled  = if Vals = null then null else List.Select(Vals, each _ <> null and _ <> ""),
            Fill    = if Filled = null or prof[n] = 0 then null else Number.Round(List.Count(Filled) / prof[n], 3),
            IsKey   = Fill = 1 and List.Count(List.Distinct(Filled)) = List.Count(Filled)
                      and List.Contains({"text", "number"}, Type)
                      and Record.FieldOrDefault(c, "hidden", false) <> true
                      and not Text.EndsWith(c[name], "_TextField") and c[name] <> "ID",
            Facet  = if Type = "other" then [] else Record.Field(c, Type),
            Name   = c[name],
            Fmt    = if Type = "dateTime" then Record.FieldOrDefault(Facet, "format", null) else null,
            LkList = if Type = "lookup" then Record.FieldOrDefault(Facet, "listId", null) else null,
            Multi  = if Type = "lookup" then Record.FieldOrDefault(Facet, "allowMultipleValues", false) else null,
            Choices = if Type = "choice"
                      then Text.Combine(List.Transform(Record.FieldOrDefault(Facet, "choices", {}), Text.From), " | ")
                      else null,
            Notes  = List.RemoveNulls({
                if Type = "lookup" then "Absent from CSV exports and from a plain REST item read. REST gives " & Name & "Id; display value via FieldValuesAsText, or this mirror's " & Name & " column." else null,
                if Type = "lookup" and Multi = true then "Multi-value: " & Name & "Id is an id ARRAY." else null,
                if Type = "dateTime" and Fmt = "dateOnly" then "Date-only: write a BARE yyyy-mm-dd. Stored as Eastern midnight, reads back ...T04:00Z/T05:00Z. A ...T00:00:00Z value is UTC midnight = the PREVIOUS day on this site (E7)." else null,
                if Type = "boolean" then "Yes/No: never-set = NULL over REST; a CSV export prints NULL as False (E6)." else null,
                if Type = "calculated" then "Calculated: reads BLANK in CSV exports." else null,
                if Text.EndsWith(Name, "_TextField") then "Mirror of a lookup; only as current as its last sync (x16). Never derive a fix from it." else null,
                if Text.Contains(Name, "Revion") then "Internal name is misspelled (Revion) - use it exactly as is." else null,
                if Name = "RevModelDescription" then "Target of a MultiChoice source; the flow takes first().Value - never write the array (R22)." else null,
                if Fill = 0 then "EMPTY on every row (fillRate 0) - never look rows up by this column." else null,
                if Fill <> null and Fill > 0 and Fill < 0.05 then "ALMOST EMPTY (" & Number.ToText(Fill * 100, "0.#") & "% filled) - do not look rows up by this column." else null,
                if IsKey then "Identifies a row: 100% filled and unique (the list's own key is always Id)." else null,
                if ByIdCol and CsvCol <> null and CsvCol <> RestCol then
                    "The mirror CSV names this id column " & CsvCol & " (Excel names are case-insensitive and " & RestCol
                    & " collides with another column) - but REST and flows still call it " & RestCol & "." else null
            }),
            Base = [
                list = listTitle,
                displayName = Record.FieldOrDefault(c, "displayName", null),
                internalName = Name,
                type = Type & (if Fmt <> null then " (" & Fmt & ")" else ""),
                lookupList = if LkList = null then null else Record.FieldOrDefault(TitleById, Text.Lower(LkList), LkList),
                lookupShowField = if Type = "lookup" then Record.FieldOrDefault(Facet, "columnName", null) else null,
                multiValue = Multi,
                choices = Choices,
                formula = if Type = "calculated" then Record.FieldOrDefault(Facet, "formula", null) else null,
                hidden = Record.FieldOrDefault(c, "hidden", null),
                readOnly = Record.FieldOrDefault(c, "readOnly", null),
                required = Record.FieldOrDefault(c, "required", null),
                indexed = Record.FieldOrDefault(c, "indexed", null),
                restField = RestCol,
                csvColumn = CsvCol,
                idColumn = if ByIdCol then CsvCol else null,
                fillRate = Fill,
                isKey = IsKey,
                notesByRule = if List.IsEmpty(Notes) then null else Text.Combine(Notes, " ")
            ]
        in
            Base,

    PerList  = (t as text) as list =>
        let
            Id   = SP_Json("_api/web/lists/getbytitle('" & t & "')", [#"$select" = "Id"])[Id],
            Data = SP_Mirror(t),
            Prof = [data = Data, map = Value.Metadata(Data)[ColumnMap], n = Table.RowCount(Data)]
        in  List.Transform(SP_ColumnsRaw(Id)[Column], (c) => Row(t, c, Prof)),
    AllRows  = List.Combine(List.Transform(Lists, PerList)),
    Table0   = Table.FromRecords(AllRows),
    Joined   = Table.NestedJoin(Table0, {"list", "internalName"}, SyncedFrom, {"list", "internalName"}, "sync", JoinKind.LeftOuter),
    Expanded = Table.ExpandTableColumn(Joined, "sync", {"syncedFromList", "syncedFromField", "syncedByFlow", "viaLookup", "readAs"}),
    Noted    = Table.AddColumn(Expanded, "notes", each Text.Combine(List.RemoveNulls({
                   if [syncedByFlow] <> null then "Written by '" & [syncedByFlow] & "' from " & [syncedFromList] & "." & [syncedFromField] & " (" & [readAs] & ") - edit the parent, not this column." else null,
                   [notesByRule]}), " "), type text),
    Out      = Table.RemoveColumns(Noted, {"notesByRule"}),
    Sorted   = Table.Sort(Out, {{"list", Order.Ascending}, {"hidden", Order.Ascending}, {"internalName", Order.Ascending}})
in
    Sorted
