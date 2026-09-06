// Query: Model Revisions
let
    Source = SharePoint.Tables("https://ermcopower.sharepoint.com/sites/PioneerPlanificatio", [Implementation = "2.0"]),
    #"Model Revisions" = Source{[Id="e2ff8703-b590-4648-b181-9b47cf3883ba"]}[Items],
    #"Flattened" = FlattenSharePointLookupLists(#"Model Revisions", SharepointListMetaColumns)
in
    #"Flattened"