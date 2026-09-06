// Query: Models SA
let
    Source = SharePoint.Tables("https://ermcopower.sharepoint.com/sites/PioneerPlanificatio", [Implementation = "2.0"]),
    #"b910b757-844f-4e0c-bfd5-05ef8fc6ea12" = Source{[Id="b910b757-844f-4e0c-bfd5-05ef8fc6ea12"]}[Items],
    #"Flattened" = FlattenSharePointLookupLists(#"b910b757-844f-4e0c-bfd5-05ef8fc6ea12", SharepointListMetaColumns),
    #"Added Custom" = Table.AddColumn(Flattened, "Parent Model", each Text.BeforeDelimiter([Model_Code], " SA"), type text)
in
    #"Added Custom"