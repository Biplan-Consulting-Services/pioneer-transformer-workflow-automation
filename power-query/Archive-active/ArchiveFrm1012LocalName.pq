// Query: ArchiveFrm1012LocalName
//
// Which workbook table holds TableArchiveFRM10_12's history (its previous rows).
//
// Normally that is TableArchiveFRM10_12 itself. The one exception is the 2026-09-28 switch
// from a Data Model load to a direct sheet load (option 2, docs/archive-build-status-2026-09-28.md):
// the old model-backed table is unlinked and renamed TableArchiveFRM10_12_Seed, and a new
// sheet-loaded TableArchiveFRM10_12 is created. On its FIRST refresh the new table is still an
// empty placeholder, so the history is taken from the seed. Every refresh after that finds
// rows in TableArchiveFRM10_12 and uses it; the seed is then deleted.
//
// Rule: TableArchiveFRM10_12 if it has an "Order" column and at least one row, else
// TableArchiveFRM10_12_Seed if it exists, else TableArchiveFRM10_12 (and the caller's
// NoLocalTable guard fails the refresh, which is what must happen when history is missing).
let
    Tables = Excel.CurrentWorkbook(),
    Has = (name as text) as logical => List.Contains(Tables[Name], name),
    RealHasRows =
        Has("TableArchiveFRM10_12")
        and (let t = Tables{[Name = "TableArchiveFRM10_12"]}[Content]
             in Table.HasColumns(t, "Order") and not Table.IsEmpty(t)),
    Name =
        if RealHasRows then "TableArchiveFRM10_12"
        else if Has("TableArchiveFRM10_12_Seed") then "TableArchiveFRM10_12_Seed"
        else "TableArchiveFRM10_12"
in
    Name
