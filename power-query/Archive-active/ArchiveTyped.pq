// Query: ArchiveTyped
//
// One of the five main lists, typed, straight from ArchiveFetch (never SharePoint.Tables).
//   title: "Order Items" | "Order" | "Models" | "Model Revisions" | "Clients"
//
// CONTRACT (what Archive <List> and the FRM10-12 adapter rely on)
//   Column names   = SharePoint INTERNAL names, exactly as the live mirror CSVs name them
//                    (Planned_x0020_Delivery_x0020_Dat, OrderNumberId, ...). Id first, then Title.
//   Id             Int64, never null, unique (ArchiveList checks).
//   <Lookup>Id     the lookup's item id, Int64 (a multi-value lookup: JSON text "[12,15]").
//   <Lookup>       its display value, text: the target item's show-field (catalog lookup
//                  facet `columnName`, else Title), resolved FROM ArchiveFetch's copy of the
//                  target list. Multi-value: "; "-joined. An id the target lacks: "?<id>".
//                  If a column called <Lookup> already exists, the display is <Lookup>_Value.
//   <Person>Id     Int64 user id (Author, Editor, any personOrGroup column).
//   <Person>_Email text: the user's email, else display name; unknown id "?<id>".
//   Types come from the LIVE catalog (ArchiveFetch[Columns]), never from a column list here, so
//   a column added on SharePoint tomorrow is read and typed without editing this file:
//     dateTime format dateOnly, calculated dateTime/dateOnly  -> date = Date.FromText(first 10 chars)
//     dateTime format dateTime (incl. Created, Modified), calculated dateTime/dateTime
//                                                             -> text, the ISO value exactly as REST sent it
//     number, currency, calculated number/currency           -> number
//     boolean, calculated boolean                            -> logical
//     text, note, choice, calculated text                    -> text
//     multi-choice, multi-lookup id arrays, URL/other records -> JSON text (never flattened, R22)
//     no facet (GUID, Attachments, OData__ColorTag, ...)      -> inferred from the values
//     a calculated value that failed on SharePoint ("error;#<n>") -> null in a date/number/logical column
//   Excel-safe names: Excel column names are case-insensitive. When two names collide ignoring
//   case, the id/derived column takes the suffix 2, 3, ... and the list's own field keeps its
//   name. Today's only case: Model Revisions `ModelID` (text) vs `ModelId` (the Model lookup id)
//   -> the id is `ModelId2`, the same name the mirror uses.
//
// Why date-only = first 10 characters: SharePoint stores a date-only value as Eastern midnight in
// UTC (T04:00Z / T05:00Z); the six E7 orders are stored at T00:00Z. The date part is right in all
// three cases; converting to local time is not (docs/archive-all-lists-design-2026-09-27.md §3).
(title as text) as table =>
let
    Fetch    = ArchiveFetch,
    Known    = if List.Contains(Fetch[Titles], title) then title
               else error Error.Record("ArchiveTyped", "'" & title & "' is not one of the archived lists: " & Text.Combine(Fetch[Titles], ", ")),
    Raw      = Record.Field(Fetch[Items], Known),
    Cols     = Record.Field(Fetch[Columns], Known),
    HasFacet = (c as record, f as text) as logical => Record.HasFields(c, f) and Value.Is(Record.Field(c, f), type record),
    FacetOf  = (c as record, f as text) as record => if HasFacet(c, f) then Record.Field(c, f) else [],
    Columns0 = Table.ColumnNames(Raw),

    // ---- 1. lookups: <name>Id present on the items + a v2.0 lookup facet (same rule as SP_Mirror)
    Lookups  = List.Select(Cols, each HasFacet(_, "lookup") and List.Contains(Columns0, _[name] & "Id")),
    TargetRows = (listId as text) as table =>
        let t = Record.FieldOrDefault(Fetch[TitleById], Text.Lower(listId), null)
        in  if t <> null and List.Contains(Fetch[Titles], t)
            then Record.Field(Fetch[Items], t)
            // Not one of the five: ONE extra read of that target (none of today's lookups do this).
            else Table.Buffer(SP_ItemsRaw("lists(guid'" & listId & "')")),
    AddLookup = (tbl as table, col as record) as table =>
        let
            TRows   = TargetRows(col[lookup][listId]),
            Show    = Record.FieldOrDefault(col[lookup], "columnName", "Title"),
            ShowCol = if Table.HasColumns(TRows, Show) then Show else "Title",
            Map     = Record.FromList(
                          List.Transform(Table.Column(TRows, ShowCol), each if _ = null then null else Text.From(_)),
                          List.Transform(Table.Column(TRows, "Id"), Text.From)),
            Resolve = (v) =>
                if v = null then null
                else if Value.Is(v, type list)
                    then Text.Combine(List.Transform(v, each Record.FieldOrDefault(Map, Text.From(_), "?" & Text.From(_))), "; ")
                else Record.FieldOrDefault(Map, Text.From(v), "?" & Text.From(v)),
            OutName = if Table.HasColumns(tbl, col[name]) then col[name] & "_Value" else col[name]
        in
            Table.AddColumn(tbl, OutName, each Resolve(Record.Field(_, col[name] & "Id")), type nullable text),
    WithLookups = List.Accumulate(Lookups, Raw, (s, c) => AddLookup(s, c)),
    LookupDisplay = List.Difference(Table.ColumnNames(WithLookups), Columns0),

    // ---- 2. people: <name>Id -> <name>_Email
    UserMap  = Record.FromList(
                   List.Transform(Fetch[Users], each if [Email] <> null and [Email] <> "" then [Email] else [Title]),
                   List.Transform(Fetch[Users], each Text.From([Id]))),
    PersonCols  = List.Select(Cols, each HasFacet(_, "personOrGroup")),
    PersonNames = List.Distinct(List.Transform(PersonCols, each _[name]) & {"Author", "Editor"}),
    People   = List.Select(PersonNames, each List.Contains(Columns0, _ & "Id")),
    WithPeople = List.Accumulate(People, WithLookups, (s, p) =>
                   Table.AddColumn(s, p & "_Email", each
                       let v = Record.Field(_, p & "Id") in
                       if v = null then null
                       else if Value.Is(v, type list) then Text.Combine(List.Transform(v, each Record.FieldOrDefault(UserMap, Text.From(_), "?" & Text.From(_))), "; ")
                       else Record.FieldOrDefault(UserMap, Text.From(v), "?" & Text.From(v)),
                   type nullable text)),
    Derived  = LookupDisplay & List.Transform(People, each _ & "_Email"),

    // ---- 3. nested values -> JSON text (multi-choice arrays, multi-lookup id arrays, URL records)
    AsJson   = (v) => if Value.Is(v, type list) or Value.Is(v, type record)
                      then Text.FromBinary(Json.FromValue(v)) else v,
    Flat     = Table.TransformColumns(WithPeople, List.Transform(Table.ColumnNames(WithPeople), each {_, AsJson})),

    // ---- 4. the kind of each column, from the live catalog
    KindOfCol = (c as record) as text =>
        let
            Dt   = FacetOf(c, "dateTime"),
            Calc = FacetOf(c, "calculated"),
            Out  = Record.FieldOrDefault(Calc, "outputType", "text")
        in
            if HasFacet(c, "dateTime")      then (if Record.FieldOrDefault(Dt, "format", null) = "dateOnly" then "date" else "isotext")
            else if HasFacet(c, "number") or HasFacet(c, "currency") then "number"
            else if HasFacet(c, "boolean")  then "logical"
            else if HasFacet(c, "calculated") then
                     (if Out = "dateTime" then (if Record.FieldOrDefault(Calc, "format", null) = "dateOnly" then "date" else "isotext")
                      else if Out = "number" or Out = "currency" then "number"
                      else if Out = "boolean" then "logical"
                      else "text")
            else if HasFacet(c, "text") or HasFacet(c, "choice") then "text"
            else if HasFacet(c, "hyperlinkOrPicture") then "text"
            else "infer",
    CatalogKinds = List.Combine(List.Transform(Cols, (c) =>
        if HasFacet(c, "lookup") then
            {{c[name] & "Id", if Record.FieldOrDefault(c[lookup], "allowMultipleValues", false) = true then "text" else "int"}}
        else if HasFacet(c, "personOrGroup") then
            {{c[name] & "Id", if Record.FieldOrDefault(c[personOrGroup], "allowMultipleSelection", false) = true then "text" else "int"}}
        else {{c[name], KindOfCol(c)}})),
    FixedKinds = {{"Id", "int"}, {"AuthorId", "int"}, {"EditorId", "int"}}
                 & List.Transform(Derived, each {_, "text"}),
    // Record.Combine: a later pair overrides an earlier one (AuthorId appears in both lists).
    KindMap  = Record.Combine(List.Transform(CatalogKinds & FixedKinds, each Record.AddField([], _{0}, _{1}))),
    Infer    = (col as text) as text =>
        let vals = List.Select(Table.Column(Flat, col), each _ <> null)
        in  if List.IsEmpty(vals) then "text"
            else if List.AllTrue(List.Transform(vals, each Value.Is(_, type logical))) then "logical"
            else if List.AllTrue(List.Transform(vals, each Value.Is(_, type number))) then "number"
            else "text",
    KindOf   = (col as text) as text =>
        let k = Record.FieldOrDefault(KindMap, col, "infer") in if k = "infer" then Infer(col) else k,

    // ---- 5. convert + type in one pass
    // A calculated column whose formula fails on SharePoint reads back as text "error;#<n>"
    // (seen 2026-09-28 on Order Items FxYear/FxRate/PriceCAD, Ids 1256-1257). That is "no value",
    // so it becomes null in a date/number/logical column rather than a cell error.
    IsCalcError = (v) => Value.Is(v, type text) and Text.StartsWith(v, "error;#"),
    ToDate   = (v) => if v = null or v = "" or IsCalcError(v) then null
                      else if Value.Is(v, type date) then v
                      else if Value.Is(v, type datetime) then Date.From(v)
                      else Date.FromText(Text.Start(Text.From(v), 10), [Format = "yyyy-MM-dd", Culture = "en-US"]),
    ToNumber = (v) => if v = null or v = "" or IsCalcError(v) then null
                      else if Value.Is(v, type number) then v
                      else Number.FromText(Text.From(v), "en-US"),
    ToLogical = (v) => if v = null or v = "" or IsCalcError(v) then null
                      else if Value.Is(v, type logical) then v
                      else if Value.Is(v, type number) then v <> 0
                      else let t = Text.Lower(Text.Trim(Text.From(v))) in
                           if t = "1" or t = "true" or t = "yes" then true
                           else if t = "0" or t = "false" or t = "no" then false
                           else error Error.Record("ArchiveTyped", "Not a yes/no value: " & Text.From(v)),
    ToText   = (v) => if v = null then null else if Value.Is(v, type text) then v else Text.From(v),
    Conv     = [date = {ToDate, type nullable date}, isotext = {ToText, type nullable text},
                number = {ToNumber, type nullable number}, int = {ToNumber, Int64.Type},
                logical = {ToLogical, type nullable logical}, text = {ToText, type nullable text}],
    Typed    = Table.TransformColumns(Flat, List.Transform(Table.ColumnNames(Flat), (col) =>
                   let k = Record.Field(Conv, KindOf(col)) in {col, k{0}, k{1}})),

    // ---- 6. order (Id, Title first, as the mirror) and Excel-safe names
    Ordered  = Table.ReorderColumns(Typed,
                   List.Intersect({{"Id", "Title"}, Table.ColumnNames(Typed)})
                   & List.Difference(Table.ColumnNames(Typed), {"Id", "Title"})),
    Names    = Table.ColumnNames(Ordered),
    IdCols   = List.Transform(Lookups, each _[name] & "Id") & List.Transform(People, each _ & "Id"),
    // Priority: the list's own fields claim their names first, then ids, then derived columns.
    Priority = List.Select(Names, each not List.Contains(IdCols & Derived, _))
               & List.Select(Names, each List.Contains(IdCols, _))
               & List.Select(Names, each List.Contains(Derived, _) and not List.Contains(IdCols, _)),
    SafeMap  = List.Accumulate(Priority, [seen = {}, pairs = {}], (s, n) =>
                   let
                       cand = (i) => if i = 1 then n else n & Text.From(i),
                       pick = List.First(List.Select({1 .. 50}, (i) => not List.Contains(s[seen], Text.Lower(cand(i)))))
                   in
                       [seen = s[seen] & {Text.Lower(cand(pick))},
                        pairs = if pick = 1 then s[pairs] else s[pairs] & {{n, cand(pick)}}])[pairs],
    Renamed  = if List.IsEmpty(SafeMap) then Ordered else Table.RenameColumns(Ordered, SafeMap)
in
    Renamed
