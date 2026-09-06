// Query: EnforceFormats
let
    EnforceFormats = (inputTable as table) as table =>
    let
        // Load the format parser table
        #"Format Parser Table" = try Excel.CurrentWorkbook(){[Name="TableFormatParser"]}[Content] otherwise null,

        // Filter for the row where Type = "Number"
        #"Number Format Row" = if #"Format Parser Table" = null then null else Table.SelectRows(#"Format Parser Table", each [Type] = "Number"){0},
        #"Enforced Characteristics" = if #"Format Parser Table" = null then null else Json.Document(#"Number Format Row"[Enforced Characteristics]),
        #"Display Characteristics" = if #"Format Parser Table" = null then null else Json.Document(#"Number Format Row"[Display Characteristics]),
        #"Needs Formatting" = if #"Format Parser Table" = null then false else #"Enforced Characteristics" = #"Display Characteristics",
        
        // Function to enforce formatting on individual cell values
        #"Enforce Format Cell" = (value) =>
            if Value.Is(value, Number.Type) then
                value // Leave as number if it's a number
            else if Value.Is(value, Text.Type) then
                let
                    textValue = value,
                    containsDigitGroupSeparator = Text.Contains(textValue, #"Display Characteristics"[digitGroupSeparator]),
                    containsDecimalSeparator = Text.Contains(textValue, #"Display Characteristics"[decimalSeparator])
                in
                    if containsDigitGroupSeparator or containsDecimalSeparator then
                        // Replace the separators and convert to text
                        Text.Replace(Text.Replace(textValue, 
                            #"Display Characteristics"[digitGroupSeparator], 
                            #"Enforced Characteristics"[digitGroupSeparator]), 
                            #"Display Characteristics"[decimalSeparator], 
                            #"Enforced Characteristics"[decimalSeparator]
                        )
                    else
                        value // Leave unchanged if neither separator is present
            else
                value, // Leave non-numeric and non-text values unchanged

        // Apply the enforced format if needed
        #"Applied Enforced Format" = if not #"Needs Formatting" then inputTable else Table.TransformColumns(inputTable, 
            List.Transform(Table.ColumnNames(inputTable), (colName) => 
                {colName, each #"Enforce Format Cell"(_)}
            )
        )
    in
        #"Applied Enforced Format"
in
    EnforceFormats