// Query: ArchiveListMetaColumns
//
// Columns to drop when archiving a SharePoint list. Deliberately NOT FRM10-12's
// `SharepointListMetaColumns`, which removes 23 columns including `ID`, `Created`,
// `Modified`, `Created By`, `Modified By` and `Title`.
//
// Those are right to drop from a working table and wrong to drop from an archive:
//
//   ID                      the only 100%-unique key on `Model Revisions`, and the
//                           fallback key everywhere else
//   Title                   IS the unit id on `Order Items` (displayed as `Unit ID`)
//   Created / Modified      when the row appeared and last changed -- the provenance
//   Created By / Modified By  who did it. An archive without this answers no audit
//                           question worth asking.
//
// So this list keeps all of those and removes only genuine UI scaffolding that carries
// no information: attachment/edit affordances, content-type plumbing, retention-label
// columns nothing here uses, and the folder/child counters.
let
    Source = {
        "Attachments",
        "Edit",
        "Type",
        "Item Child Count",
        "Folder Child Count",
        "Label setting",
        "Retention label",
        "Retention label Applied",
        "Label applied by",
        "Item is a Record",
        "App Created By",
        "App Modified By",
        "Content Type",
        "Compliance Asset Id",
        "Color Tag"
    }
in
    Source
