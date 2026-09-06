// Query: ImportDefinedValueFromIndex
(sheet, name) =>
let
    Path = Table.SelectRows(Index, each [Title] = sheet){0}[Path],
    Workbook = Excel.Workbook(Web.Contents(Path), null, true),
    #"Defined Value" = Workbook{[Item=name, Kind="DefinedName"]}[Data][Column1]{0}
in
    #"Defined Value"