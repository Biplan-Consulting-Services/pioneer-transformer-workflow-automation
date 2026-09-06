// Query: ImportFromIndex
(sheet, name) =>
let
    Path = Table.SelectRows(Index, each [Title] = sheet){0}[Path],
    Workbook = Excel.Workbook(Web.Contents(Path), null, true),
    Table = Workbook{[Item=name,Kind="Table"]}[Data],
    #"Cleaned table" = ReplaceAllErrors(Table, null)
in
    #"Cleaned table"