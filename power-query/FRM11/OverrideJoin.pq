// Query: OverrideJoin
let
    OverrideJoin = (MainTable as table, MainJoinKey as text, OverrideTable as table, OverrideJoinKey as text) =>
    let
        OverridePrefix = "Override.",
        JoinedPrefix = "Joined.",
        MergeKey = "OverrideTable",
        #"Main Table Columns" = Table.ColumnNames(MainTable),
        #"Main Table Column Types" = List.Zip({#"Main Table Columns", List.Transform(#"Main Table Columns", each Type.TableColumn(Value.Type(MainTable), _))}),
        #"Override Table Columns" = Table.ColumnNames(OverrideTable),
        #"Override Columns" =  List.Intersect({#"Main Table Columns", #"Override Table Columns"}),
        #"Override Columns with Prefix" = List.Transform(#"Override Columns", each OverridePrefix & _),
        #"Joined Columns with Prefix" = List.Transform(#"Override Columns", each JoinedPrefix & _),
        #"Merged Tables" = Table.NestedJoin(
            MainTable, {MainJoinKey}, 
            OverrideTable, {OverrideJoinKey}, 
            MergeKey, JoinKind.LeftOuter
        ),
        #"Expanded Merged Tables" = Table.ExpandTableColumn(#"Merged Tables", MergeKey, #"Override Columns", #"Override Columns with Prefix"),
        #"Joined Values" = List.Accumulate(
            #"Override Columns", 
            #"Expanded Merged Tables", 
            (state, col) => 
                let
                    OverrideCol = OverridePrefix & col,
                    JoinedCol = JoinedPrefix & col,
                    #"Added Join Column" = Table.AddColumn(state, JoinedCol, each if Record.Field(_, OverrideCol) <> null then Record.Field(_, OverrideCol) else Record.Field(_, col))
                in
                    #"Added Join Column"
        ),
        #"Removed Base Columns" = Table.RemoveColumns(#"Joined Values", #"Override Columns"),
        #"Removed Override Columns" = Table.RemoveColumns(#"Removed Base Columns", #"Override Columns with Prefix"),
        #"Renamed Joined Columns" = Table.RenameColumns(#"Removed Override Columns", List.Zip({#"Joined Columns with Prefix", #"Override Columns"})),
        #"Selected columns" = Table.SelectColumns(#"Renamed Joined Columns", #"Main Table Columns"),
        #"Restored Types" = Table.TransformColumnTypes(#"Selected columns", #"Main Table Column Types"),
        #"Missing Rows" = Table.NestedJoin(
            MainTable, {MainJoinKey}, 
            OverrideTable, {OverrideJoinKey}, 
            MergeKey, JoinKind.RightAnti
        ),
        #"Removed Columns" = Table.RemoveColumns(#"Missing Rows", {MergeKey}),
        #"Combined with Missing Rows" = Table.Combine({#"Restored Types", #"Removed Columns"})
    in
        #"Combined with Missing Rows"
in
    OverrideJoin