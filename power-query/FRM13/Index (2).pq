// Query: Index (2)
let
    Source = SharePoint.Tables("https://ermcopower.sharepoint.com/sites/PioneerPlanificatio"),
    Index = Source{[Name="Index"]}[Content],
    #"Removed Other Columns" = Table.SelectColumns(Index,{"Title", "Path"}),
    #"Regularised hyperlinks" = Table.TransformColumns(#"Removed Other Columns", {"Path", each if Text.Length(_) > 0 then Text.BeforeDelimiter(_, ",", {0, RelativePosition.FromEnd}) else _}),
    #"Buffered Table" = Table.Buffer(#"Regularised hyperlinks")
in
    #"Buffered Table"