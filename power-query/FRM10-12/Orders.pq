// Query: Orders
let
    Source = SharePoint.Tables("https://ermcopower.sharepoint.com/sites/PioneerPlanificatio", [Implementation = "2.0"]),
    Orders = Source{[Title="Order"]}[Items],
    #"Flattened orders" = FlattenSharePointLookupLists(Orders, SharepointListMetaColumns)
in
    #"Flattened orders"