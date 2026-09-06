// Query: StackList
let
    Source = Excel.CurrentWorkbook(){[Name="StackList"]}[Content],
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"StackList", type text}})
in
    #"Changed Type"