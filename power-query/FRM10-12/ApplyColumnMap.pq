// Query: ApplyColumnMap
// Renames and retypes a source table's columns per Other Queries/ColumnMap.pq, for a
// given entity ("Models", "Model Revisions", "Orders", ...).
//
// Validates first: if the source is missing a column ColumnMap.pq expects, this raises
// a clear error naming exactly which expected column(s) are missing and what columns
// actually exist - instead of the cryptic "field wasn't found" error you'd otherwise
// only see deep in a downstream merge step.
(sourceTable as table, entity as text) as table =>
let
    TypeFromCode = (code as text) as type =>
        if code = "text" then type text
        else if code = "number" then type number
        else if code = "date" then type date
        else if code = "datetime" then type datetime
        else if code = "logical" then type logical
        else type any,

    MapRows = Table.SelectRows(ColumnMap, each [Entity] = entity),
    ExpectedSourceCols = Table.Column(MapRows, "SourceField"),
    ActualCols = Table.ColumnNames(sourceTable),
    MissingCols = List.Difference(ExpectedSourceCols, ActualCols),

    Checked =
        if List.Count(MissingCols) > 0 then
            error Error.Record(
                "ColumnMap.MissingColumns",
                "ColumnMap.pq expects """ & entity & """ to have column(s) " &
                    Text.Combine(List.Transform(MissingCols, each """" & _ & """"), ", ") &
                    " but they weren't found. Actual columns on this source: " &
                    Text.Combine(List.Transform(ActualCols, each """" & _ & """"), ", ") &
                    ". Either SharePoint renamed/removed the field, or ColumnMap.pq is out of date for entity """ & entity & """.",
                [Entity = entity, MissingSourceColumns = MissingCols, ActualColumns = ActualCols]
            )
        else
            sourceTable,

    Renamed = Table.RenameColumns(Checked, List.Zip({MapRows[SourceField], MapRows[WorkbookField]}), MissingField.Ignore),
    Typed = Table.TransformColumnTypes(Renamed, List.Zip({MapRows[WorkbookField], List.Transform(MapRows[Type], TypeFromCode)}))
in
    Typed