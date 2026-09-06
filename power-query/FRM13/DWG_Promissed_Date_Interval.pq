// Query: DWG_Promissed_Date_Interval
let
    Source = Excel.CurrentWorkbook(){[Name="DWG_Promissed_Date_Interval"]}[Content],
    Column10 = Source{0}[Column1]
in
    Column10