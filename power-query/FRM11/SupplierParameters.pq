// Query: SupplierParameters
(name) =>
let
    #"Supplier Parameters" = Table.SelectRows(TableSuppliers, each [Supplier] = name){0}
in
    #"Supplier Parameters"