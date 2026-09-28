// Query: Archive Models
//
// SharePoint list `Models`, archived by item Id into TableArchiveModels (ArchiveList).
let
    Source = ArchiveList("Models", "TableArchiveModels")
in
    Source
