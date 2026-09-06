// Query: SupplierReport
let
    GenerateSupplierData = (Supplier as text) as table =>
    let
        // Getting Supplier Params
        #"Supplier Parameters" = SupplierParameters(Supplier),

        // Getting Orders linked with Supplier from FournTank
        #"Filtered for Supplier" = Table.SelectRows(FournTank, each ([Fournisseur CUVE] = Supplier or [Fournisseur Peinture] = Supplier)),
        #"Columns to Import" = Table.SelectRows(
            TableLocales, 
            each [Imported From Pioneer] 
                and (if #"Supplier Parameters"[Supplies Tank] then [In Tank Suppliers] else true) 
                and (if #"Supplier Parameters"[Supplies Paint] then [In Paint Suppliers] else true)
        )[Standard name],
        #"Valid Columns to Import" = List.Intersect({#"Columns to Import", Table.ColumnNames(FournTank)}),
        #"Supplier Orders" = Table.SelectColumns(#"Filtered for Supplier", #"Valid Columns to Import"),

        // Fetching data from supplier side
        #"Supplier Data Import" = ImportFromIndex(#"Supplier Parameters"[Indexed Report Name], "TableReport"),
        #"Imported Column Names" = Table.ColumnNames(#"Supplier Data Import"),
        #"Valid Imported Column Names" =  List.Intersect({#"Imported Column Names", #"Supplier Imported Columns"}),
        #"Merged Import" = Table.NestedJoin(
            #"Supplier Orders", 
            {"NUMÉRO DE CUVE"}, 
            #"Supplier Data Import", 
            {"NUMÉRO DE CUVE"}, 
            "Import", 
            JoinKind.LeftOuter
        ),
        #"Expanded Import" = Table.ExpandTableColumn(
            #"Merged Import", 
            "Import", 
            #"Valid Imported Column Names", 
            #"Valid Imported Column Names"
        ),
        
        // Fetching local data (self-ref)
        #"Local Table" = Excel.CurrentWorkbook(){[Name=#"Supplier Parameters"[Table Name]]}[Content],
        #"Valid Self-Ref Columns" = List.Intersect({#"Supplier Self-Ref Columns", Table.ColumnNames(#"Local Table")}),
        #"Merged Local Table" = Table.NestedJoin(
            #"Expanded Import", 
            {"NUMÉRO DE CUVE"}, 
            #"Local Table", 
            {"NUMÉRO DE CUVE"}, 
            "LocalTable", 
            JoinKind.LeftOuter
        ),    
        #"Expanded Local Table" = Table.ExpandTableColumn(
            #"Merged Local Table", 
            "LocalTable", 
            #"Valid Self-Ref Columns", 
            #"Valid Self-Ref Columns"
        ),
        
        // Removing duplicates and finalizing columns
        #"Removed Duplicates" = Table.Distinct(#"Expanded Local Table", {"NUMÉRO DE CUVE"}),
        #"Valid Columns" = List.Intersect({TableLocales[Standard name], Table.ColumnNames(#"Removed Duplicates")}),
        #"Reordered Columns" = Table.ReorderColumns(#"Removed Duplicates", #"Valid Columns"),
        #"Columns to Exclude" = Table.SelectRows(TableSupplierExclusions, each [Supplier] = Supplier)[Column],
        #"Valid Columns to Exclude" = List.Intersect({Table.ColumnNames(#"Reordered Columns"), #"Columns to Exclude"}),
        #"Excluded Columns" = Table.RemoveColumns(#"Reordered Columns", #"Valid Columns to Exclude")
    in
        #"Excluded Columns"
in
    GenerateSupplierData