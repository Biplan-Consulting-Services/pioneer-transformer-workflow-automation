// Query: ClientLeadTimes
let
    Source = ImportFromIndex("FRM13-Auto", "LeedTime"),
    // Rename + type, driven by ColumnMap.pq (entity "ClientLeadTimes")
    #"Applied Column Map" = ApplyColumnMap(Source, "ClientLeadTimes")
in
    #"Applied Column Map"