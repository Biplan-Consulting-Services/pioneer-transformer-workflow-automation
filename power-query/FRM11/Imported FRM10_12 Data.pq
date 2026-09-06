// Query: Imported FRM10_12 Data
let
    Source = FRM10_12,
    #"Removed Other Columns" = Table.SelectColumns(Source,{"Order", "Client", "Type", "KVA and KV", "PO Item #", "Location", "Tanking Date", "Original Tanking Date", "Tanking date change justification", "Tank"}),
    #"Renamed Columns" = Table.RenameColumns(#"Removed Other Columns",{{"Order", "NUMÉRO DE CUVE"}, {"Client", "CLIENT"}, {"PO Item #", "DUP ou # Client"}, {"Location", "location"}, {"Tanking Date", "Date encuvage"}}),
    #"Removed Hyperlinks" = #"Remove Hyperlinks"(#"Renamed Columns", {"NUMÉRO DE CUVE", "CLIENT", "Type", "KVA and KV"}),
    #"Added Custom" = Table.AddColumn(#"Removed Hyperlinks", "CLIENT, TYPE TRANSFO, SIZE", each (if [CLIENT] = null then "" else Text.From([CLIENT])) & " - " & (if [Type] = null then "" else Text.From([Type])) & " " & (if [KVA and KV] = null then "" else Text.From([KVA and KV])), type text),
    #"Merged Queries" = Table.NestedJoin(#"Added Custom", {"Tank"}, #"Verbose Tank Codes Ref", {"Code"}, "Verbose Tank Codes Ref", JoinKind.LeftOuter),
    #"Expanded Verbose Tank Codes Ref" = Table.ExpandTableColumn(#"Merged Queries", "Verbose Tank Codes Ref", {"Statut"}, {"Status"}),
    #"Removed Columns" = Table.RemoveColumns(#"Expanded Verbose Tank Codes Ref",{"KVA and KV", "Tank"})
in
    #"Removed Columns"