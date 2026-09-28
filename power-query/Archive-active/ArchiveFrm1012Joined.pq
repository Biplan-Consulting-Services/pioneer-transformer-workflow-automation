// Query: ArchiveFrm1012Joined
//
// One row per Order Items unit, with every field the column map needs from the unit and
// its parents, joined BY LOOKUP ID (source rule: parent data from the parent list, never
// from the unit's copy columns). Columns are named "<List>.<internal field>", so the map's
// SourceList + SourceField IS the column name here, and nothing can collide.
//
//   Order Items  --OrderNumberId-->   Order  --ClientId-->  Clients
//   Order Items  --ModelRevisionId--> Model Revisions
//   plus, by unit id (Title = Order):
//     "TableArchiveBO.<col>"  from ArchiveLocalBO          (D2 backfill)
//     "Previous.<col>"        from ArchiveFrm1012Previous  (legacy + BO persistence)
//
// Models is not joined: no FRM10-12 column comes from it (every spec field lives on Model
// Revisions). Add a Joins row if one ever does.
//
// Reads SharePoint ONLY through ArchiveTyped (agent A's typed reader: internal names, Id
// as Int64, lookup ids as `<Name>Id` Int64). Only the fields the map uses are kept. A field
// the live catalog (ArchiveFetch[Columns]) does not know is an ERROR naming it; a known field
// that no item carries (SP_ItemsRaw only sees fields items have) reads as null.
let
    Map = Table.Buffer(ArchiveFrm1012Map),

    Joins = {
        [Child = "Order Items", ChildKey = "OrderNumberId",   Parent = "Order",           ParentKey = "Id"],
        [Child = "Order Items", ChildKey = "ModelRevisionId", Parent = "Model Revisions", ParentKey = "Id"],
        [Child = "Order",       ChildKey = "ClientId",        Parent = "Clients",         ParentKey = "Id"]
    },
    Lists = {"Order Items", "Order", "Model Revisions", "Clients"},
    KeyField = "Title",   // Order Items' unit id (display "Unit ID") = archive `Order`

    // Refs inside Arg ("<List>.<field>") for the rules that read other fields.
    RefRules = {"ec", "status", "ingdue", "navorder", "navmodel"},
    ArgTokens = List.Combine(List.Transform(
        Table.SelectRows(Map, each List.Contains(RefRules, [Rule]))[Arg],
        each Text.Split(_, ";"))),

    FieldsFor = (list as text) as list =>
        List.Distinct(List.Combine({
            if list = "Order Items" then {KeyField} else {},
            Table.SelectRows(Map, each [SourceList] = list)[SourceField],
            List.Transform(List.Select(ArgTokens, each Text.StartsWith(_, list & ".")),
                           each Text.Range(_, Text.Length(list) + 1)),
            List.Transform(List.Select(Joins, each [Child] = list), each [ChildKey]),
            List.Transform(List.Select(Joins, each [Parent] = list), each [ParentKey])
        })),

    Fetch = (list as text) as table =>
        let
            Raw = ArchiveTyped(list),
            Need = FieldsFor(list),
            Absent = List.Difference(Need, Table.ColumnNames(Raw)),
            // SP_ItemsRaw builds its columns from the fields items actually carry, so a column
            // that exists on the list but is empty on every item can be absent. That is not an
            // error: it reads as null. A field the live CATALOG does not know is one (renamed
            // or removed on SharePoint, or a wrong map row).
            CatalogNames = List.Transform(Record.Field(ArchiveFetch[Columns], list), each _[name]),
            Known = (f as text) as logical =>
                f = "Id" or List.Contains(CatalogNames, f)
                or (Text.EndsWith(f, "Id") and List.Contains(CatalogNames, Text.Start(f, Text.Length(f) - 2))),
            Missing = List.Select(Absent, each not Known(_)),
            Picked =
                if List.IsEmpty(Missing) then Table.SelectColumns(Raw, Need, MissingField.UseNull)
                else error Error.Record(
                    "ArchiveFrm1012Joined.MissingField",
                    "ArchiveFrm1012Map needs field(s) " & Text.Combine(Missing, ", ") & " from """ & list
                        & """ but ArchiveTyped did not return them. SharePoint renamed/removed a column, or the map is wrong.",
                    [List = list, Missing = Missing])
        in
            Table.PrefixColumns(Picked, list),

    // --- the row source: Order Items, keyed on Title ---
    UnitsRaw = Fetch("Order Items"),
    Key = "Order Items." & KeyField,
    Units = Table.SelectRows(UnitsRaw, each Record.Field(_, Key) <> null and Text.Trim(Text.From(Record.Field(_, Key))) <> ""),
    DupUnits = Table.SelectRows(Table.Group(Units, {Key}, {{"n", Table.RowCount, Int64.Type}}), each [n] > 1),
    UnitsChecked =
        if Table.IsEmpty(DupUnits) then Table.TransformColumns(Units, {{Key, Text.From, type text}})
        else error Error.Record(
            "ArchiveFrm1012Joined.DuplicateOrder",
            "Order Items has " & Text.From(Table.RowCount(DupUnits)) & " duplicate Unit ID (Title) value(s): "
                & Text.Combine(List.FirstN(Table.Column(DupUnits, Key), 20), ", ")
                & ". The archive is keyed on it; fix the duplicates on SharePoint.",
            [Duplicates = Table.Column(DupUnits, Key)]),

    // --- parents, by lookup id ---
    Joined = List.Accumulate(
        Joins,
        UnitsChecked,
        (acc, j) => Table.Join(
            acc, j[Child] & "." & j[ChildKey],
            Table.Buffer(Fetch(j[Parent])), j[Parent] & "." & j[ParentKey],
            JoinKind.LeftOuter)),

    // --- local inputs, by unit id ---
    WithBO = Table.Join(Joined, Key, Table.PrefixColumns(ArchiveLocalBO, "TableArchiveBO"), "TableArchiveBO.Order", JoinKind.LeftOuter),
    WithPrevious = Table.Join(WithBO, Key, Table.PrefixColumns(ArchiveFrm1012Previous, "Previous"), "Previous.Order", JoinKind.LeftOuter),

    // A parent Id or local key matching twice would multiply units; never let that pass.
    Checked =
        if Table.RowCount(WithPrevious) = Table.RowCount(UnitsChecked) then WithPrevious
        else error Error.Record(
            "ArchiveFrm1012Joined.RowCountChanged",
            "Joining Order Items to its parents changed the row count from " & Text.From(Table.RowCount(UnitsChecked))
                & " to " & Text.From(Table.RowCount(WithPrevious)) & ": a parent Id or local key is duplicated.",
            null)
in
    Table.Buffer(Checked)
