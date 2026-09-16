// Query: Archive Order
//
// 457/457 unique. `Order` has no archive of any kind today.
let
    Source = TrackRemoteList("Order", "TableArchiveOrder", "Order Number")
in
    Source
