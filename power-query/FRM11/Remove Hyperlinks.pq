// Query: Remove Hyperlinks
(tbl as table, columns as list) as table =>
let
    TransformColumn = (value as any) as any =>
        let
            Result =
                if not Value.Is(value, type text) then
                    value
                else if Text.Contains(value, "IF(TRUE, HYPERLINK") then
                    let
                        QuotePositions = Text.PositionOf(value, """", Occurrence.All),
                        QuoteCount = List.Count(QuotePositions),
                        Extracted =
                            if QuoteCount >= 2 then
                                Text.Middle(
                                    value,
                                    QuotePositions{QuoteCount - 2} + 1,
                                    QuotePositions{QuoteCount - 1} - QuotePositions{QuoteCount - 2} - 1
                                )
                            else
                                value
                    in
                        Extracted
                else
                    value
        in
            Result,

    Transformations =
        List.Transform(
            columns,
            each {_, TransformColumn, type any}
        ),

    Result =
        Table.TransformColumns(
            tbl,
            Transformations
        )
in
    Result