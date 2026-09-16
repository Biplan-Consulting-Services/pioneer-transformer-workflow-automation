// Query: Archive Order Items
//
// `Title` is the unit id (displayed `Unit ID`); 1085/1085 unique. This is the one
//   that closes the 22-column gap -- tracking the LIST, not FRM10-12's TableOrders.
let
    Source = TrackRemoteList("Order Items", "TableArchiveOrderItems", "Title")
in
    Source
