// Query: Models
let
    Source = SharePoint.Tables("https://ermcopower.sharepoint.com/:l:/r/sites/PioneerPlanificatio/", [Implementation=null, ApiVersion=15]),
    #"b43a5140-0f9d-4ac1-9019-43b897074224" = Source{[Id="b43a5140-0f9d-4ac1-9019-43b897074224"]}[Items],
    #"Changed Type" = Table.TransformColumnTypes(#"b43a5140-0f9d-4ac1-9019-43b897074224",{{"ModelName", type text}})
in
    #"Changed Type"