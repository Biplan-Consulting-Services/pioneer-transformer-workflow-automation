// Query: Archive Model Revisions
//
// SharePoint list `Model Revisions`, archived by item Id into TableArchiveModelRevisions
// (ArchiveList). The Model lookup's id is `ModelId2` here: `ModelID` (text) already holds the
// case-insensitive name `ModelId` in Excel (see ArchiveTyped, "Excel-safe names").
let
    Source = ArchiveList("Model Revisions", "TableArchiveModelRevisions")
in
    Source
