// Query: ArchiveFRM10_12
let
    Source = ImportFromIndex("Archive active", "TableArchiveFRM10_12"),
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"Order", type text}})
in
    #"Changed Type"