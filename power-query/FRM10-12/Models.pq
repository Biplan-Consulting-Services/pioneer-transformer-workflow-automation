// Query: Models
let
    Source = SharePoint.Tables("https://ermcopower.sharepoint.com/sites/PioneerPlanificatio", [Implementation = "2.0"]),
    Models = Source{[Title="Models"]}[Items],
    #"Flattened orders" = FlattenSharePointLookupLists(Models, SharepointListMetaColumns)
in
    #"Flattened orders"