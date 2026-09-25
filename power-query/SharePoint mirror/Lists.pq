// E10 step 0 - one row per mirrored list: its version-history settings and counts.
// The change-tracking design's rollback FALLBACK is SharePoint item version history,
// so it only holds if versioning is ON and the limit is not tiny. `versioningOk`
// says so per list; anything false needs a list-settings change before relying on it.
let
    Lists  = {"Order Items", "Order", "Models", "Model Revisions", "Clients", "Index", "Models SA"},
    Fields = "Id,Title,ItemCount,EnableVersioning,MajorVersionLimit,EnableMinorVersions,"
           & "MajorWithMinorVersionsLimit,ForceCheckout,EnableModeration,Created,"
           & "LastItemModifiedDate,LastItemUserModifiedDate,LastItemDeletedDate",
    Read   = (t as text) as record =>
        let
            r = SP_Json("_api/web/lists/getbytitle('" & t & "')", [#"$select" = Fields]),
            on = Record.FieldOrDefault(r, "EnableVersioning", false),
            lim = Record.FieldOrDefault(r, "MajorVersionLimit", null)
        in
            [
                list = t,
                listId = r[Id],
                itemCount = Record.FieldOrDefault(r, "ItemCount", null),
                versioningEnabled = on,
                majorVersionLimit = lim,
                minorVersionsEnabled = Record.FieldOrDefault(r, "EnableMinorVersions", null),
                majorWithMinorLimit = Record.FieldOrDefault(r, "MajorWithMinorVersionsLimit", null),
                forceCheckout = Record.FieldOrDefault(r, "ForceCheckout", null),
                contentApproval = Record.FieldOrDefault(r, "EnableModeration", null),
                created = Record.FieldOrDefault(r, "Created", null),
                lastItemModified = Record.FieldOrDefault(r, "LastItemModifiedDate", null),
                lastItemUserModified = Record.FieldOrDefault(r, "LastItemUserModifiedDate", null),
                lastItemDeleted = Record.FieldOrDefault(r, "LastItemDeletedDate", null),
                // 0 = unlimited on SharePoint Online; otherwise the number of major versions kept.
                versioningOk = on = true and lim <> null and (lim = 0 or lim >= 50),
                note = if on <> true then "VERSIONING OFF - no per-item history, rollback fallback unavailable"
                       else if lim = null then "version limit unreadable"
                       else if lim = 0 then "versioning on, no limit"
                       else if lim < 50 then "versioning on but only " & Text.From(lim) & " versions kept - bulk edits can push history out"
                       else "versioning on, " & Text.From(lim) & " major versions kept"
            ],
    Out    = Table.FromRecords(List.Transform(Lists, Read))
in
    Out
