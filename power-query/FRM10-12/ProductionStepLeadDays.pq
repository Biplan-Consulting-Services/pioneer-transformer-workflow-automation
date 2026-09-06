// Query: ProductionStepLeadDays
let
    Source = Excel.CurrentWorkbook(){[Name="TableParametersDays"]}[Content],
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"Assignation par défaut pour livraison (jours)", type number}, {"Isolation", type number}, {"Bobinage", type number}, {"Enrouleur", type number}, {"Assembleur", type number}, {"Encuveur", type number}, {"Essais", type number}, {"Monteur", type number}, {"Soudeur", type number}, {"Finition", type number}})
in
    #"Changed Type"