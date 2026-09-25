// READ-ONLY probe (board, D6 follow-up): what keeps writing a few items?
// One row per KEPT version of each probed item: when, who, and which fields changed from
// the previous kept version, with old -> new values. Only the kept versions exist to read
// (limit 50 + the current one), so an item with label 851 shows its LAST 51 only.
//
// Edit PROBES to point it elsewhere; list title + item id.
let
    PROBES = {[list = "Order Items", id = 126], [list = "Model Revisions", id = 26]},
    // Bookkeeping fields that change on every version by definition - not evidence.
    Meta   = {"VersionId", "VersionLabel", "IsCurrentVersion", "Created", "Modified", "Editor", "Author",
              "Created_x0020_Date", "Last_x0020_Modified", "OData__UIVersionString", "OData__UIVersion",
              "Modified_x0020_By", "Created_x0020_By", "owshiddenversion", "GUID", "UniqueId",
              "_UIVersionString", "_UIVersion", "SMLastModifiedDate", "SMTotalSize", "ContentVersion",
              "OData__ModerationStatus", "OData__Level", "OData__IsCurrentVersion"},
    Show   = (v) => if v = null then "null"
                    else if Value.Is(v, type list) or Value.Is(v, type record) then Text.FromBinary(Json.FromValue(v))
                    else Text.From(v),
    Cut    = (s as text) => if Text.Length(s) > 60 then Text.Start(s, 57) & "..." else s,
    One    = (p as record) as list =>
        let
            Id      = SP_Json("_api/web/lists/getbytitle('" & p[list] & "')", [#"$select" = "Id"])[Id],
            Vs      = SP_Json("_api/web/lists(guid'" & Id & "')/items(" & Text.From(p[id]) & ")/versions",
                              [#"$top" = "5000"])[value],
            // oldest first: sort by the numeric version label
            Num     = (v) => Number.From(Text.BeforeDelimiter(Text.From(v[VersionLabel]), ".")),
            Sorted  = List.Sort(Vs, (a, b) => Value.Compare(Num(a), Num(b))),
            Rows    = List.Transform({0 .. List.Count(Sorted) - 1}, (i) =>
                let
                    cur   = Sorted{i},
                    prev  = if i = 0 then null else Sorted{i - 1},
                    keys  = List.Difference(Record.FieldNames(cur), Meta),
                    changed = if prev = null then {}
                              else List.Select(keys, (k) => Show(Record.FieldOrDefault(cur, k, null)) <> Show(Record.FieldOrDefault(prev, k, null))),
                    ed    = Record.FieldOrDefault(cur, "Editor", null),
                    edTxt = if ed = null then null
                            else if Value.Is(ed, type record) then Record.FieldOrDefault(ed, "Email", Record.FieldOrDefault(ed, "LookupValue", null))
                            else Text.From(ed)
                in
                    [
                        list = p[list], itemId = p[id], version = Num(cur),
                        modified = Record.FieldOrDefault(cur, "Modified", null),
                        editor = edTxt,
                        firstKept = i = 0,
                        nChanged = List.Count(changed),
                        changedFields = Text.Combine(changed, ", "),
                        changes = Text.Combine(List.Transform(changed, (k) =>
                                      k & ": " & Cut(Show(Record.FieldOrDefault(prev, k, null))) & " -> " & Cut(Show(Record.FieldOrDefault(cur, k, null)))), " | ")
                    ])
        in
            Rows,
    Out = Table.FromRecords(List.Combine(List.Transform(PROBES, One)))
in
    Out
