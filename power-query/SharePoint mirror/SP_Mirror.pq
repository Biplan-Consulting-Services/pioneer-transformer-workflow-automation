// One list, mirrored: every raw REST field (internal names, <Lookup>Id ints, raw date
// text), PLUS for each lookup its display value in a column named after the lookup
// (e.g. `ModelId` = 463 and `Model` = "1147005"), PLUS <Person>_Email for each
// person column. This is the shape x22/x25 join on - ids, not display text.
//
// Why not FRM10-12's FlattenSharePointLookupLists: it replaces a lookup with its
// display text and drops the id, and its meta-column list strips ID/Created/Modified.
//
// Nested values (URL {Description,Url}, MultiChoice arrays, multi-lookup id arrays)
// are written as JSON text - never flattened to a guess. A MultiChoice read as
// ["PADMOUNT"] is the R22 trap; seeing the brackets here is the point.
(listTitle as text) as table =>
let
    ListId   = SP_Json("_api/web/lists/getbytitle('" & listTitle & "')", [#"$select" = "Id"])[Id],
    Raw      = SP_ItemsRaw("lists(guid'" & ListId & "')"),
    Cols     = SP_ColumnsRaw(ListId)[Column],

    // ---- lookups: <name>Id present on the items + a v2.0 lookup facet
    Lookups  = List.Select(Cols, each Record.HasFields(_, "lookup")
                                  and Table.HasColumns(Raw, _[name] & "Id")),
    AddLookup = (tbl as table, col as record) as table =>
        let
            TargetId = col[lookup][listId],
            Show     = Record.FieldOrDefault(col[lookup], "columnName", "Title"),
            TRows    = SP_ItemsRaw("lists(guid'" & TargetId & "')"),
            ShowCol  = if Table.HasColumns(TRows, Show) then Show else "Title",
            Map      = Record.FromList(
                           List.Transform(Table.Column(TRows, ShowCol), each if _ = null then null else Text.From(_)),
                           List.Transform(Table.Column(TRows, "Id"), Text.From)),
            Resolve  = (v) =>
                if v = null then null
                else if Value.Is(v, type list)
                    then Text.Combine(List.Transform(v, each Record.FieldOrDefault(Map, Text.From(_), "?" & Text.From(_))), "; ")
                else Record.FieldOrDefault(Map, Text.From(v), "?" & Text.From(v)),
            OutName  = if Table.HasColumns(tbl, col[name]) then col[name] & "_Value" else col[name]
        in
            Table.AddColumn(tbl, OutName, each Resolve(Record.Field(_, col[name] & "Id")), type nullable text),
    WithLookups = List.Accumulate(Lookups, Raw, (s, c) => AddLookup(s, c)),

    // ---- people: <name>Id -> <name>_Email (Author, Editor, and any person column)
    Users    = SP_Json("_api/web/siteusers", [#"$select" = "Id,Email,Title"])[value],
    UserMap  = Record.FromList(
                   List.Transform(Users, each if [Email] <> null and [Email] <> "" then [Email] else [Title]),
                   List.Transform(Users, each Text.From([Id]))),
    PersonNames = List.Distinct(
                   List.Transform(List.Select(Cols, each Record.HasFields(_, "personOrGroup")), each _[name])
                   & {"Author", "Editor"}),
    People   = List.Select(PersonNames, each Table.HasColumns(WithLookups, _ & "Id")),
    WithPeople = List.Accumulate(People, WithLookups, (s, p) =>
                   Table.AddColumn(s, p & "_Email", each
                       let v = Record.Field(_, p & "Id") in
                       if v = null then null
                       else if Value.Is(v, type list) then Text.Combine(List.Transform(v, each Record.FieldOrDefault(UserMap, Text.From(_), "?" & Text.From(_))), "; ")
                       else Record.FieldOrDefault(UserMap, Text.From(v), "?" & Text.From(v)),
                   type nullable text)),

    // ---- nested values -> JSON text, so Excel and the CSV see exactly what REST sent
    AsJson   = (v) => if Value.Is(v, type list) or Value.Is(v, type record)
                      then Text.FromBinary(Json.FromValue(v)) else v,
    Flat     = Table.TransformColumns(WithPeople,
                   List.Transform(Table.ColumnNames(WithPeople), each {_, AsJson})),

    Ordered  = Table.ReorderColumns(Flat,
                   List.Intersect({{"Id", "Title"}, Table.ColumnNames(Flat)})
                   & List.Difference(Table.ColumnNames(Flat), {"Id", "Title"})),

    // ---- Excel-safe names, decided HERE rather than by Excel. Excel column names are
    // case-insensitive, so REST's `ModelID` (text) and `ModelId` (the Model lookup's id) on Model
    // Revisions collide and Excel silently renames the later one to `ModelId2`. Doing the same rule
    // ourselves (later duplicate gets 2, 3, ...) keeps today's names AND lets the Columns catalog
    // know the real CSV column (meta ColumnMap: REST name -> CSV name) instead of guessing.
    Names    = Table.ColumnNames(Ordered),
    Safe     = List.Accumulate(Names, [seen = {}, out = {}], (s, n) =>
                   let
                       cand = (i) => if i = 1 then n else n & Text.From(i),
                       pick = List.First(List.Select({1 .. 50}, (i) => not List.Contains(s[seen], Text.Lower(cand(i)))))
                   in
                       [seen = s[seen] & {Text.Lower(cand(pick))}, out = s[out] & {cand(pick)}])[out],
    Pairs    = List.Select(List.Zip({Names, Safe}), (p) => p{0} <> p{1}),
    Renamed  = if List.IsEmpty(Pairs) then Ordered else Table.RenameColumns(Ordered, Pairs)
in
    Renamed meta [ColumnMap = Record.FromList(Safe, Names)]
