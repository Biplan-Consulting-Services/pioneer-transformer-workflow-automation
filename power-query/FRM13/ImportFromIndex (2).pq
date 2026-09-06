// Query: ImportFromIndex (2)
let
    Source = (sheet, name) =>
let
    Path = Table.SelectRows(#"Index (2)", each [Title] = sheet){0}[Path],
    Workbook = Excel.Workbook(Web.Contents(Path), null, true),
    Table = Workbook{[Item=name,Kind="Table"]}[Data],
    #"Cleaned table" = #"ReplaceAllErrors (2)"(Table, null)
in
    #"Cleaned table"
in
    Source