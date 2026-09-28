// Query: ArchiveFrm1012Previous
//
// TableArchiveFRM10_12's own current values for the columns SharePoint can NOT be trusted
// to resupply, keyed on Order:
//   `legacy` rows  (Duplicate, Duplicate Order, Archived ... Production Status): never on
//                  SharePoint. A unit still on the list keeps what the archive already had,
//                  instead of AccumulateIntoLocal overwriting it with null. This matters now
//                  that D4 re-sends units the viewer had stopped sending (freeze-at-LI dropped).
//   `bo` rows      the last fallback of the D2 rule, so a BO value backfilled from
//                  TableArchiveBO survives that table's removal.
// Staging query: workbook only.
let
    Columns = Table.SelectRows(ArchiveFrm1012Map, each [Rule] = "legacy" or [Rule] = "bo")[TargetColumn],
    Source = ArchiveLocalTable(ArchiveFrm1012LocalName, "Order", Columns)   // the archive or its one-time seed
in
    Source
