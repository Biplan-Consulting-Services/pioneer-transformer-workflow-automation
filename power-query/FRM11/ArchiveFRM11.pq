// Query: ArchiveFRM11
let
    Source = ImportFromIndex("Archive active", "TableArchiveFRM11"),
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"NUMÉRO DE CUVE", type text}})
in
    #"Changed Type"