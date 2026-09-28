// Query: ArchiveLocalBO
//
// TableArchiveBO's BO + BO1..BO3 detail, keyed on Order (unit id): the D2 BACKFILL source.
// The columns are the map's `bo` rows, whose TargetColumn names are TableArchiveBO's own
// header names, so no second list exists to drift.
//
// Returns an empty table once TableArchiveBO is removed; `Archive FRM10-12` then relies on
// its own previous values (see the `bo` rule there). Staging query: it touches only the
// workbook, so the adapter never mixes a workbook read and a SharePoint read in one step.
let
    BOColumns = Table.SelectRows(ArchiveFrm1012Map, each [Rule] = "bo")[TargetColumn],
    Source = ArchiveLocalTable("TableArchiveBO", "Order", BOColumns)
in
    Source
