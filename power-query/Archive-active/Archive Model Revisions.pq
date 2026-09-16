// Query: Archive Model Revisions
//
// ⚠️ `ID`, not `Model_Revion_ID` (sic): that column is blank on 1 of 391 rows, and a
//   null key cannot match in the anti-join -- the row would be re-added forever.
//   Fill that one blank and this can move to the natural key.
let
    Source = TrackRemoteList("Model Revisions", "TableArchiveModelRevisions", "ID")
in
    Source
