// Query: Archive Order
//
// SharePoint list `Order`, archived by item Id into TableArchiveOrder (ArchiveList).
// The order number is Order_x0020_Number1 (`Title` is empty on every row); the key is Id.
let
    Source = ArchiveList("Order", "TableArchiveOrder")
in
    Source
