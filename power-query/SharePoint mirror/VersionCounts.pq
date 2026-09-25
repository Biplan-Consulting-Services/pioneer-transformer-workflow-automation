// D6 evidence - how much version history each list's items are using, per list.
//
// Uses OData__UIVersionString ("37.0") on EVERY item - no sampling. Its major number is how
// many major versions the item has ever had; it keeps counting after the version limit
// trims old ones. So:
//   label <= limit  -> all history still kept
//   label >  limit  -> the oldest (label - limit) versions are already GONE
// To prove the label is not something else, the busiest item of each list also gets its
// versions actually COUNTED (`keptOnTopItem`): it equals min(label, limit + 1) - the
// /versions list holds the `limit` history versions PLUS the current one (measured 22:33).
let
    Lists  = {"Order Items", "Order", "Models", "Model Revisions", "Clients", "Index", "Models SA"},
    Pct    = (sorted as list, p as number) as nullable number =>
                 if List.IsEmpty(sorted) then null
                 else sorted{Number.RoundUp(p * List.Count(sorted)) - 1},
    PerList = (t as text) as record =>
        let
            Meta    = SP_Json("_api/web/lists/getbytitle('" & t & "')", [#"$select" = "Id,MajorVersionLimit"]),
            Page    = SP_Json("_api/web/lists(guid'" & Meta[Id] & "')/items",
                              [#"$select" = "Id,OData__UIVersionString", #"$top" = "5000"]),
            Items   = if Record.HasFields(Page, "odata.nextLink")
                      then error Error.Record("VersionCounts", "More than 5000 items in " & t & ": paging needed")
                      else Page[value],
            Pairs   = List.Transform(Items, each [id = [Id],
                          v = Number.From(Text.BeforeDelimiter(Text.From(Record.FieldOrDefault(_, "OData__UIVersionString", "0")), "."))]),
            Vs      = List.Sort(List.Transform(Pairs, each [v])),
            Limit   = Meta[MajorVersionLimit],
            Top     = List.Last(List.Sort(Pairs, (a, b) => Value.Compare(a[v], b[v]))),
            Kept    = List.Count(SP_Json("_api/web/lists(guid'" & Meta[Id] & "')/items(" & Text.From(Top[id]) & ")/versions",
                                         [#"$select" = "VersionLabel", #"$top" = "5000"])[value])
        in
            [
                list = t,
                items = List.Count(Vs),
                versionLimit = Limit,
                median = Pct(Vs, 0.5),
                p95 = Pct(Vs, 0.95),
                max = List.Max(Vs),
                atOrOver40 = List.Count(List.Select(Vs, each _ >= 40)),
                overLimit_historyLost = List.Count(List.Select(Vs, each Limit > 0 and _ > Limit)),
                topItemId = Top[id],
                topItemLabel = Top[v],
                keptOnTopItem = Kept,
                labelCheck = if Kept = (if Limit > 0 then List.Min({Top[v], Limit + 1}) else Top[v])
                             then "ok: kept = min(label, limit + 1) (limit + the current version)"
                             else "MISMATCH: kept " & Text.From(Kept) & " vs label " & Text.From(Top[v])
            ],
    Out    = Table.FromRecords(List.Transform(Lists, PerList))
in
    Out
