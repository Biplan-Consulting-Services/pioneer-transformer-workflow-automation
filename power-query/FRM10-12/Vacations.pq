// Query: Vacations
let
    Source = Excel.CurrentWorkbook(){[Name="TableVacations"]}[Content],
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"Vacance", type text}, {"Début", type date}, {"Fin", type date}})
in
    #"Changed Type"