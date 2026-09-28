// Query: Archive Clients
//
// SharePoint list `Clients`, archived by item Id into TableArchiveClients (ArchiveList).
let
    Source = ArchiveList("Clients", "TableArchiveClients")
in
    Source
