// Query: TrackRemoteList
//
// 🟠 OBSOLETE (2026-09-28): use ArchiveList(title, localTable) directly. Kept only as a thin
// compatibility wrapper so an old call cannot silently fall back to the 09-16 draft.
//
// The 09-16 draft read SharePoint.Tables, which shifts date-only values a day early (found
// 2026-09-24), flattened lookups to display text, and keyed lists on Title / natural keys. All of
// that is gone: this now goes through the REST reader (ArchiveFetch -> ArchiveTyped ->
// ArchiveList) and accepts ONLY the item Id as key. Any other key raises an error instead of
// archiving under the wrong key.
//
// Only the five main lists are archived (decision A1); a list outside them errors in ArchiveTyped.
// The 09-16 drafts `Archive EngineeringChangeOrders`, `Archive ModelChanges`, `Archive Models SA`
// call this with natural keys and are therefore NOT applicable (they were never in the workbook).
let
    TrackRemoteList = (ListTitle as text, LocalTable as text, PrimaryKey as text) as table =>
        if PrimaryKey <> "Id"
        then error Error.Record("TrackRemoteList", "Obsolete: archive lists are keyed on 'Id' only (got '" & PrimaryKey & "'). Use ArchiveList(title, localTable).")
        else ArchiveList(ListTitle, LocalTable)
in
    TrackRemoteList
