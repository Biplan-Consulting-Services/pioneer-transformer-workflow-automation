// Query: ReplaceAllErrors
(dataset, placeholder) =>
let
    ColumnsList = Table.ColumnNames(dataset),
    ColumnsNullList = List.Transform(ColumnsList, each {_, placeholder}),
    #"Replaced Errors" = Table.ReplaceErrorValues(dataset, ColumnsNullList)
in
    #"Replaced Errors"