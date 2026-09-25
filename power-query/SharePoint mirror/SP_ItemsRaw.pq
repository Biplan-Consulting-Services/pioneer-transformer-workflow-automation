// Every item of one list, RAW: internal names, values exactly as REST returns them.
//   listPath: "lists/getbytitle('Order Items')"  or  "lists(guid'd6468ec5-...')"
//
// Rules this enforces (each is a lesson from the console scripts):
//   - A zero-row read is a FAILED read, not an empty list -> error.
//   - One page of $top=5000 covers every list here (largest ~1,200). If SharePoint
//     still hands back a nextLink, the mirror would be silently truncated -> error
//     instead of guessing at paging.
//   - Column set = the UNION of every item's fields. REST omits a field an item
//     never had set on some lists, so the first record alone is not the schema.
//   - Nothing is typed. Dates stay as the raw "2026-09-01T00:00:00Z" text - the E7
//     one-day defect lives in that text, and a datetime conversion could hide it.
(listPath as text) as table =>
let
    Page   = SP_Json("_api/web/" & listPath & "/items", [#"$top" = "5000"]),
    More   = Record.HasFields(Page, "odata.nextLink"),
    Items  = if More
             then error Error.Record("SP_ItemsRaw", "More than 5000 items in " & listPath & ": paging needed, refusing to truncate.")
             else Page[value],
    Checked = if List.Count(Items) = 0
              then error Error.Record("SP_ItemsRaw", "Read 0 items from " & listPath & ". A zero-row read is a failed read.")
              else Items,
    Names  = List.Distinct(List.Combine(List.Transform(Checked, Record.FieldNames))),
    Noise  = {"FileSystemObjectType", "ServerRedirectedEmbedUri", "ServerRedirectedEmbedUrl",
              "ContentTypeId", "ComplianceAssetId", "OData__UIVersionString", "ID"},
    Keep   = List.Difference(Names, Noise),
    Table  = Table.FromRecords(Checked, Keep, MissingField.UseNull)
in
    Table
