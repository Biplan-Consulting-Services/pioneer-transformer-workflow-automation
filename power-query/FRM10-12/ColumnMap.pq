// Query: ColumnMap
// Central reference for how raw external field names (SharePoint lists, or tables in
// linked workbooks) map onto the workbook's field names and types, for the entities
// where this has been centralized so far (Models, Model Revisions, Models SA, Orders,
// ClientLeadTimes). Consumed by functions/ApplyColumnMap.pq.
//
// When the external source renames/retypes a field: update the row here, don't go
// hunting through every .pq file that touches this entity.
//
// Type codes recognized by ApplyColumnMap: text, number, date, datetime, logical.
// Use "any" (or leave a note) when the real type isn't confirmed yet against live data.
let
    Source = Table.FromRecords({

        // --- Orders (raw list name: "Order") ---
        [Entity = "Orders", SourceField = "Order Number", WorkbookField = "Order Number", Type = "text", Notes = "Merge key"],
        [Entity = "Orders", SourceField = "Client", WorkbookField = "Client", Type = "text", Notes = "Lookup to Clients list"],
        [Entity = "Orders", SourceField = "Order Type", WorkbookField = "Order Type", Type = "text", Notes = ""],
        [Entity = "Orders", SourceField = "Model", WorkbookField = "PO Item #", Type = "text", Notes = "Lookup to Models/Models SA"],
        [Entity = "Orders", SourceField = "Order Date", WorkbookField = "Order Date", Type = "date", Notes = ""],
        [Entity = "Orders", SourceField = "Qty", WorkbookField = "Qty", Type = "text", Notes = "Kept as text, not numeric - existing values aren't safely parseable as pure numbers"],
        [Entity = "Orders", SourceField = "Initial Promised Date", WorkbookField = "Initial Promised Date", Type = "date", Notes = ""],
        [Entity = "Orders", SourceField = "PO", WorkbookField = "PO", Type = "text", Notes = ""],
        [Entity = "Orders", SourceField = "Price", WorkbookField = "Price Value", Type = "number", Notes = ""],
        [Entity = "Orders", SourceField = "Province/State", WorkbookField = "Province/State", Type = "text", Notes = ""],
        [Entity = "Orders", SourceField = "WET-WETP", WorkbookField = "WET-WETP", Type = "text", Notes = ""],
        [Entity = "Orders", SourceField = "Indexing", WorkbookField = "Indexing", Type = "text", Notes = ""],
        [Entity = "Orders", SourceField = "SA", WorkbookField = "SA", Type = "logical", Notes = ""],

        // --- Models (raw list name: "Models") ---
        // Only identity/workflow fields that stay on Models after the Model Revisions
        // migration. Technical spec fields live under the "Model Revisions" entity below.
        [Entity = "Models", SourceField = "Model_Code", WorkbookField = "PO Item #", Type = "text", Notes = "Merge key"],
        [Entity = "Models", SourceField = "Notes", WorkbookField = "Technical Notes", Type = "text", Notes = ""],
        [Entity = "Models", SourceField = "Info+", WorkbookField = "Info+", Type = "text", Notes = ""],
        [Entity = "Models", SourceField = "Protector & Switchgear Item #", WorkbookField = "Protector & Switchgear Item #", Type = "text", Notes = ""],
        [Entity = "Models", SourceField = "Configuration", WorkbookField = "Configuration", Type = "text", Notes = ""],
        [Entity = "Models", SourceField = "Section Qty", WorkbookField = "Section Qty", Type = "number", Notes = ""],

        // --- Model Revisions (raw list name: "Model Revisions") ---
        // Technical spec fields migrated off Models. "Model Description" is a
        // multi-choice list field on the SharePoint side - TableOrders.pq flattens it
        // to a comma-joined string BEFORE this map's rename/type step runs, so by the
        // time it gets here it's already a plain scalar.
        [Entity = "Model Revisions", SourceField = "JS #", WorkbookField = "JS #", Type = "text", Notes = ""],
        [Entity = "Model Revisions", SourceField = "Model Type", WorkbookField = "Type", Type = "text", Notes = ""],
        [Entity = "Model Revisions", SourceField = "Model Description", WorkbookField = "Description", Type = "text", Notes = "Flattened from a multi-choice list before this map runs"],
        [Entity = "Model Revisions", SourceField = "kVA", WorkbookField = "KVA and KV", Type = "text", Notes = ""],
        [Entity = "Model Revisions", SourceField = "Primary Voltage", WorkbookField = "Primary Voltage", Type = "number", Notes = "Assumed numeric (kV) - existing rows are still blank, not yet confirmed against a populated value"],
        [Entity = "Model Revisions", SourceField = "Secondary Voltage", WorkbookField = "Secondary Voltage", Type = "number", Notes = "Assumed numeric (kV) - existing rows are still blank, not yet confirmed against a populated value"],
        [Entity = "Model Revisions", SourceField = "Oil Type", WorkbookField = "Oil Type", Type = "text", Notes = ""],
        [Entity = "Model Revisions", SourceField = "Oil Amount", WorkbookField = "Oil Amount", Type = "number", Notes = ""],
        [Entity = "Model Revisions", SourceField = "Core Type", WorkbookField = "Core", Type = "text", Notes = ""],
        [Entity = "Model Revisions", SourceField = "Phases", WorkbookField = "Phases", Type = "number", Notes = ""],
        [Entity = "Model Revisions", SourceField = "Cable", WorkbookField = "Cable", Type = "text", Notes = ""],
        [Entity = "Model Revisions", SourceField = "Form", WorkbookField = "Form", Type = "text", Notes = ""],
        [Entity = "Model Revisions", SourceField = "Copper (LV)", WorkbookField = "Copper (LV)", Type = "text", Notes = ""],
        [Entity = "Model Revisions", SourceField = "Wire (HV)", WorkbookField = "Wire (HV)", Type = "text", Notes = ""],
        [Entity = "Model Revisions", SourceField = "Overcoil", WorkbookField = "Overcoil", Type = "text", Notes = ""],

        // --- ClientLeadTimes (linked workbook "FRM13-Auto", table "LeedTime" -
        // not a SharePoint list, imported via functions/ImportFromIndex.pq) ---
        [Entity = "ClientLeadTimes", SourceField = "CLIENT", WorkbookField = "Client", Type = "text", Notes = "Merge key - renamed for consistency with TableOrders' own Client field"],
        [Entity = "ClientLeadTimes", SourceField = "Lead time", WorkbookField = "Lead Time", Type = "number", Notes = ""]
    })
in
    Source