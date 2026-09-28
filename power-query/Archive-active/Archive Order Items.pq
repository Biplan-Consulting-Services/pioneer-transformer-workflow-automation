// Query: Archive Order Items
//
// SharePoint list `Order Items`, archived by item Id into TableArchiveOrderItems (ArchiveList).
// Internal column names, typed from the live catalog; rows that leave SharePoint are kept.
// Carries the unit's own BO / BO1..BO3 part fields (plan D2).
let
    Source = ArchiveList("Order Items", "TableArchiveOrderItems")
in
    Source
