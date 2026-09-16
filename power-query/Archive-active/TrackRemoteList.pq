// Query: TrackRemoteList
//
// The SharePoint-list sibling of TrackRemoteTable. Same accumulate semantics, same
// archive table shape; the ONLY difference is where the source rows come from.
//
//     TrackRemoteTable  reads an Excel table in another workbook, via the Index list
//     TrackRemoteList   reads a SharePoint list directly
//
// This is what lets the Excel archive cover the lists that live only in SharePoint and
// have no workbook to be tracked through -- `Order`, `Models`, `Model Revisions`,
// `Clients`, `ModelChanges` -- and to track `Order Items` as itself rather than as
// FRM10-12's `TableOrders`, which is how 22 populated columns ended up unarchived.
//
// ⚠️ META COLUMNS: do NOT reuse FRM10-12's `SharepointListMetaColumns` here. That list
// strips `ID`, `Created`, `Modified` and `Title` -- sensible for a working table, wrong
// for an archive, where those four are the provenance you most want to keep, and where
// `Title` IS the unit id on `Order Items`. `ArchiveListMetaColumns` is the archive's own,
// deliberately much shorter, list.
//
// ⚠️ UNTESTED AS WRITTEN -- authored in the repo, not yet run against the workbook.
// Apply with Stage-PowerQuery.ps1 / Sync-PowerQuery.ps1 -WorkbookPath "...\Archive active.xlsx",
// and see docs/archive-cover-all-lists-2026-09-16.md for the order of operations. The
// first refresh of a NEW archive table is the dangerous one; that doc explains why.
let
    TrackRemoteList = (ListTitle as text, LocalTable as text, PrimaryKey as text) as table =>
    let
        Site = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio",
        // Implementation 2.0 pages at ~1000+ rows instead of the legacy endpoint's 100.
        Source = SharePoint.Tables(Site, [Implementation = "2.0"]),
        List = Source{[Title = ListTitle]}[Items],
        // Lookups arrive as nested lists/records; flatten to their display text.
        Flattened = FlattenSharePointLookupLists(List, ArchiveListMetaColumns),
        Accumulated = AccumulateIntoLocal(Flattened, LocalTable, PrimaryKey)
    in
        Accumulated
in
    TrackRemoteList
