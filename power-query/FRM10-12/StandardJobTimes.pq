// Query: StandardJobTimes
let
    Source = ImportFromIndex("Temps Standard", "TableJobTimes"),
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"Numéro JobScope", type text}, {"Client", type text}, {"Part Number", type text}, {"#DUP", type text}, {"Type", type text}, {"KVA", type text}, {"Quantity", type number}, {"Poids (kg)", type number}, {"Nb jours à produire", type number}, {"Total", type number}, {"Finition MOY", type number}, {"Soudeur MOY", type number}, {"Monteur (MIT)", type number}, {"Essais MOY", type number}, {"Encuveur MOY", type number}, {"Assembleur MOY", type number}, {"Enrouleur MOY", type number}, {"Bobinage MOY", type number}, {"Isolation MOY", type number}, {"Hauteur (mm)", type number}, {"Largeur (mm)", type number}, {"Profondeur (mm)", type number}, {"Fiabilité des données", type text}})
in
    #"Changed Type"