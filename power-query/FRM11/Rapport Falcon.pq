// Query: Rapport Falcon
let
    //TODO: Generalize this feature eventually
    Supplier = "FALCON",
    LocalesKPsAndColumns = #table({"Column Name", "Locales KP", "Locales Table"}, {
        {"Tank Status", "Statuts cuve", ImportFromIndex("Rapport Falcon", "TableStatutsCuve")}
    }),
    SuppliersTranslation = ImportDefinedValueFromIndex("Rapport Falcon", "SelectedLanguage"),
    UsesTranslation = List.Contains(Table.ColumnNames(LocalesKPsAndColumns[Locales Table]{0}), SuppliersTranslation),
    Source = SupplierReport(Supplier),
    FinalColumnOrder = Table.ColumnNames(Source),
    #"Translated Report" = if not UsesTranslation then Source else List.Accumulate(Table.ToRecords(LocalesKPsAndColumns), Source, (state, current) => 
        let
            #"Merged Translation" = Table.NestedJoin(state, current[Column Name], current[Locales Table], SuppliersTranslation, "Merged Translation", JoinKind.LeftOuter),
            #"Expanded Translation" = Table.ExpandTableColumn(#"Merged Translation", "Merged Translation", {current[Locales KP]}, {"Translated Column"}),
            #"Removed Column" = Table.RemoveColumns(#"Expanded Translation", {current[Column Name]}),
            #"Renamed Translated Column" = Table.RenameColumns(#"Removed Column", {{"Translated Column", current[Column Name]}})
        in
            #"Renamed Translated Column"
    ),
    #"Ensured Column Order" = if UsesTranslation then Table.ReorderColumns(#"Translated Report", FinalColumnOrder) else Source
in
    #"Ensured Column Order"