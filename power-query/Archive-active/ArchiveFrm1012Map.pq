// Query: ArchiveFrm1012Map
//
// THE COLUMN MAP of `TableArchiveFRM10_12`, and the enforcement of its source rule.
// One row per pinned target column, in pinned order: the 93 legacy columns of the
// 2026-09-27 23:56 archive, then TableArchiveBO's 18 BO detail columns (plan D2) = 111.
// `Archive FRM10-12` is driven by this table: it produces exactly these columns, in this
// order, with these rules and types, and errors if any is missing.
// Spec: docs/archive-frm10-12-column-recipe.md. Checks: scripts/check_frm1012_map.py
// (parses THIS file; keep one record per line in the exact field order below).
//
// SourceList / SourceField
//   A list title ("Order Items", "Order", "Model Revisions", "Clients") and that list's
//   INTERNAL field name, as returned by ArchiveTyped. Parent data comes from the parent
//   list, joined by lookup id (see ArchiveFrm1012Joined). "Order Items" supplies only the
//   unit's own fields: never a sync copy (Ord*/Rev*/Mdl*/Cli*, syncedFromList in the
//   mirror's Columns catalog) and never a *_TextField. The checker enforces all of this
//   against sharepoint-lists/mirror/live/Columns.csv.
//   "computed" = built from other values (the refs are in Arg).
//   "legacy"   = never produced by SharePoint: the row keeps its previous archive value.
//   "archive"  = maintained by AccumulateIntoLocal (Last Synchronisation Date).
//
// Rule (Arg)
//   copy          the value as is
//   multichoice   multi-choice JSON text '["A","B"]' -> "A, B"; '[]' -> null
//   marker (L)    true -> the letter L staff typed, false/null -> null (never false)
//   yn            true -> "Y", false/null -> null (never "N": see viewer ValueConversions)
//   loccode       Location display name -> two-letter code via LocationCodes; unmapped passes
//   ec (ref)      "EC" when the stage's status field (ref) is "In Progress", else the date
//   default (n)   null -> n
//   status (refs) composite stamp from Step Status;Status Date, falls back to stored Status
//   ingdue (refs) (TankingDate, else Initial Promised Date) - (Lead Time + 4) * 7 days
//   navorder (ref)  "Ouvrir commande " & text before the first "-"; null without a "-"
//   navmodel (ref)  "Ouvrir modèle " & PO Item #; null when PO Item # is blank
//   legacy        the row's previous value in TableArchiveFRM10_12 (null for a new row)
//   bo            first non-blank of: the Order Items field, TableArchiveBO's same-named
//                 column, the row's previous archive value. Blank = null, "", whitespace,
//                 or false. See `Archive FRM10-12` for why the third fallback exists.
//   archive       set by AccumulateIntoLocal
//   A ref in Arg is "<List>.<internal field>" (a source field) or a TargetColumn name (a
//   value already built by a non-computed row). Several refs are separated by ";".
//
// Type (what the Data Model load receives)
//   text, number, date, logical  the real type. Chosen only where EVERY value already in
//                 the archive converts (checked by check_frm1012_map.py --base).
//   datetext      a date column whose history also holds non-dates ("EC", "ANed", ".", FALSE,
//                 "pickup 2025-01-06"...). Loaded as text, dates written ISO yyyy-MM-dd, which
//                 the refresher's step 8 (convertDateTextToDates) turns into real dates, the
//                 same end state as today. Typing these as date would error those cells.
//   numtext       a number column whose history also holds text ("24.9 kV", "100-104",
//                 "Inconnu", "WC", "hq"). Loaded as text; numbers written fr-CA ("24,9"),
//                 which is how the viewer route wrote them.
//
// Basis
//   viewer        must agree with the FRM10-12 viewer's ColumnMap (entity + field, display
//                 name resolved to internal name) and ValueConversions. Checked.
//   anything else names why this row departs from the viewer: D2/D3 (plan decisions),
//                 source-rule, recipe, StatusStampCodes, legacy, archive.
let
    Source = Table.FromRecords({
        [Position = 1, TargetColumn = "Order", SourceList = "Order Items", SourceField = "Title", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 2, TargetColumn = "Client", SourceList = "Clients", SourceField = "Title", Rule = "copy", Arg = null, Type = "text", Basis = "source-rule"],
        [Position = 3, TargetColumn = "KVA and KV", SourceList = "Model Revisions", SourceField = "kVA_x0020_and_x0020_kV", Rule = "copy", Arg = null, Type = "numtext", Basis = "viewer"],
        [Position = 4, TargetColumn = "Primary Voltage", SourceList = "Model Revisions", SourceField = "PrimaryVoltage", Rule = "copy", Arg = null, Type = "number", Basis = "viewer"],
        [Position = 5, TargetColumn = "Secondary Voltage", SourceList = "Model Revisions", SourceField = "SecondaryVoltage", Rule = "copy", Arg = null, Type = "number", Basis = "viewer"],
        [Position = 6, TargetColumn = "Phases", SourceList = "Model Revisions", SourceField = "Phases", Rule = "copy", Arg = null, Type = "number", Basis = "viewer"],
        [Position = 7, TargetColumn = "JS #", SourceList = "Model Revisions", SourceField = "JS_x0020__x0023_", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 8, TargetColumn = "Description", SourceList = "Model Revisions", SourceField = "Description", Rule = "multichoice", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 9, TargetColumn = "Type", SourceList = "Model Revisions", SourceField = "Model_x0020_Type", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 10, TargetColumn = "PO", SourceList = "Order", SourceField = "PO", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 11, TargetColumn = "Order Date", SourceList = "Order", SourceField = "Order_x0020_Date", Rule = "copy", Arg = null, Type = "date", Basis = "viewer"],
        [Position = 12, TargetColumn = "Lead Time", SourceList = "Clients", SourceField = "CliLeadTimeWeeks", Rule = "default", Arg = "26", Type = "number", Basis = "D3"],
        [Position = 13, TargetColumn = "Ing. Due Date", SourceList = "computed", SourceField = "computed", Rule = "ingdue", Arg = "Order Items.TankingDate;Initial Promised Date;Lead Time", Type = "date", Basis = "recipe"],
        [Position = 14, TargetColumn = "Qty", SourceList = "Order Items", SourceField = "Qty", Rule = "copy", Arg = null, Type = "number", Basis = "viewer"],
        [Position = 15, TargetColumn = "PO Item #", SourceList = "Model Revisions", SourceField = "ModelName", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 16, TargetColumn = "Family", SourceList = "Model Revisions", SourceField = "Family", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 17, TargetColumn = "Duplicate", SourceList = "legacy", SourceField = "legacy", Rule = "legacy", Arg = null, Type = "text", Basis = "legacy"],
        [Position = 18, TargetColumn = "Engineering Required", SourceList = "Order", SourceField = "EngineeringRequired", Rule = "yn", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 19, TargetColumn = "Duplicate Order", SourceList = "legacy", SourceField = "legacy", Rule = "legacy", Arg = null, Type = "text", Basis = "legacy"],
        [Position = 20, TargetColumn = "Price", SourceList = "Order", SourceField = "Price", Rule = "default", Arg = "0", Type = "number", Basis = "D3"],
        [Position = 21, TargetColumn = "Province/State", SourceList = "Order", SourceField = "Province_x002F_State", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 22, TargetColumn = "WET-WETP", SourceList = "Order", SourceField = "WET_x002d_WETP", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 23, TargetColumn = "Indexing", SourceList = "Order", SourceField = "Indexing", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 24, TargetColumn = "LDs", SourceList = "Order", SourceField = "LDs", Rule = "yn", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 25, TargetColumn = "Initial Promised Date", SourceList = "Order", SourceField = "Initial_x0020_Promised_x0020_Dat", Rule = "copy", Arg = null, Type = "date", Basis = "viewer"],
        [Position = 26, TargetColumn = "Trimestrial Customer", SourceList = "Order Items", SourceField = "TrimestrialCustomer", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 27, TargetColumn = "Client Date Status", SourceList = "Order", SourceField = "ClientDateStatus", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 28, TargetColumn = "Info+", SourceList = "Order Items", SourceField = "Info_x002b_", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 29, TargetColumn = "Protector Status", SourceList = "Order Items", SourceField = "ProtectorStatus", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 30, TargetColumn = "Protector & Switchgear PO", SourceList = "Order Items", SourceField = "ProtectorSwitchgearPO", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 31, TargetColumn = "Protector & Switchgear Item #", SourceList = "Order Items", SourceField = "Protector_x0020__x0026__x0020_Sw", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 32, TargetColumn = "Sales Notes", SourceList = "Order", SourceField = "SalesNotes", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 33, TargetColumn = "Technical Notes", SourceList = "Order Items", SourceField = "Technical_x0020_Notes", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 34, TargetColumn = "Location", SourceList = "Order Items", SourceField = "Location", Rule = "loccode", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 35, TargetColumn = "Status", SourceList = "computed", SourceField = "computed", Rule = "status", Arg = "Order Items.StepStatus;Order Items.StatusDate;Order Items.Status", Type = "text", Basis = "StatusStampCodes"],
        [Position = 36, TargetColumn = "Witness/Other", SourceList = "Order Items", SourceField = "Witness_x002f_Other", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 37, TargetColumn = "Temperature Rise", SourceList = "Order Items", SourceField = "TemperatureRise", Rule = "marker", Arg = "x", Type = "text", Basis = "viewer"],
        [Position = 38, TargetColumn = "Impulse", SourceList = "Order Items", SourceField = "Impulse", Rule = "marker", Arg = "x", Type = "text", Basis = "viewer"],
        [Position = 39, TargetColumn = "DB", SourceList = "Order Items", SourceField = "DB", Rule = "marker", Arg = "x", Type = "text", Basis = "viewer"],
        [Position = 40, TargetColumn = "Partial D", SourceList = "Order Items", SourceField = "PartialD", Rule = "marker", Arg = "x", Type = "text", Basis = "viewer"],
        [Position = 41, TargetColumn = "Oil Analysis", SourceList = "Order Items", SourceField = "OilAnalysis", Rule = "marker", Arg = "x", Type = "text", Basis = "viewer"],
        [Position = 42, TargetColumn = "SFRA", SourceList = "Order Items", SourceField = "SFRA", Rule = "marker", Arg = "Y", Type = "text", Basis = "viewer"],
        [Position = 43, TargetColumn = "CSA", SourceList = "Order Items", SourceField = "CSA", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 44, TargetColumn = "Core", SourceList = "Model Revisions", SourceField = "Core_x0020_Type", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 45, TargetColumn = "Core Status", SourceList = "Order Items", SourceField = "CoreStatus", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 46, TargetColumn = "Oil Type", SourceList = "Model Revisions", SourceField = "Oil_x0020_Type", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 47, TargetColumn = "Oil Amount", SourceList = "Model Revisions", SourceField = "OilAmount", Rule = "copy", Arg = null, Type = "numtext", Basis = "viewer"],
        [Position = 48, TargetColumn = "Production Line", SourceList = "Order Items", SourceField = "ProductionLine", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 49, TargetColumn = "Configuration", SourceList = "Order Items", SourceField = "Configuration", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 50, TargetColumn = "Section Qty", SourceList = "Order Items", SourceField = "Section_x0020_Qty", Rule = "copy", Arg = null, Type = "numtext", Basis = "viewer"],
        [Position = 51, TargetColumn = "Cable", SourceList = "Model Revisions", SourceField = "Cable", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 52, TargetColumn = "Coil Winder", SourceList = "Order Items", SourceField = "CoilWinder", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 53, TargetColumn = "Form", SourceList = "Model Revisions", SourceField = "Form", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 54, TargetColumn = "Copper (LV)", SourceList = "Model Revisions", SourceField = "Copper_x0028_LV_x0029_", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 55, TargetColumn = "Wire (HV)", SourceList = "Model Revisions", SourceField = "Wire_x0028_HV_x0029_", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 56, TargetColumn = "Overcoil", SourceList = "Model Revisions", SourceField = "Overcoil", Rule = "copy", Arg = null, Type = "numtext", Basis = "viewer"],
        [Position = 57, TargetColumn = "Winder", SourceList = "Order Items", SourceField = "Winder", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 58, TargetColumn = "Time (days)", SourceList = "Order Items", SourceField = "Time_x0028_days_x0029_", Rule = "copy", Arg = null, Type = "numtext", Basis = "viewer"],
        [Position = 59, TargetColumn = "Tank", SourceList = "Order Items", SourceField = "Tank", Rule = "marker", Arg = "R", Type = "text", Basis = "viewer"],
        [Position = 60, TargetColumn = "Tank Delivery Date", SourceList = "Order Items", SourceField = "TankDeliveryDate", Rule = "copy", Arg = null, Type = "datetext", Basis = "viewer"],
        [Position = 61, TargetColumn = "Frame", SourceList = "Order Items", SourceField = "Frame", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 62, TargetColumn = "ISO Stack", SourceList = "Order Items", SourceField = "ISOStack", Rule = "marker", Arg = "R", Type = "text", Basis = "viewer"],
        [Position = 63, TargetColumn = "ISO Coil", SourceList = "Order Items", SourceField = "ISOCoil", Rule = "marker", Arg = "R", Type = "text", Basis = "viewer"],
        [Position = 64, TargetColumn = "Lead Assembly", SourceList = "Order Items", SourceField = "LeadAssembly", Rule = "marker", Arg = "R", Type = "text", Basis = "viewer"],
        [Position = 65, TargetColumn = "Coiling Date", SourceList = "Order Items", SourceField = "CoilingDate", Rule = "ec", Arg = "Order Items.CoilingStatus", Type = "datetext", Basis = "viewer"],
        [Position = 66, TargetColumn = "Stacking Date", SourceList = "Order Items", SourceField = "StackingDate", Rule = "ec", Arg = "Order Items.StackingStatus", Type = "datetext", Basis = "viewer"],
        [Position = 67, TargetColumn = "Assembly Date", SourceList = "Order Items", SourceField = "AssemblyDate", Rule = "ec", Arg = "Order Items.AssemblyStatus", Type = "datetext", Basis = "viewer"],
        [Position = 68, TargetColumn = "Drying Date", SourceList = "Order Items", SourceField = "DryingDate", Rule = "ec", Arg = "Order Items.DryingStatus", Type = "datetext", Basis = "viewer"],
        [Position = 69, TargetColumn = "Tanking Date", SourceList = "Order Items", SourceField = "Planned_x0020_Tanking_x0020_Date", Rule = "copy", Arg = null, Type = "datetext", Basis = "viewer"],
        [Position = 70, TargetColumn = "Testing Date", SourceList = "Order Items", SourceField = "TestingDate", Rule = "ec", Arg = "Order Items.TestingStatus", Type = "datetext", Basis = "viewer"],
        [Position = 71, TargetColumn = "Finishing Date", SourceList = "Order Items", SourceField = "FinishingDate", Rule = "ec", Arg = "Order Items.FinishingStatus", Type = "datetext", Basis = "viewer"],
        [Position = 72, TargetColumn = "Delivery Date", SourceList = "Order Items", SourceField = "Planned_x0020_Delivery_x0020_Dat", Rule = "copy", Arg = null, Type = "date", Basis = "viewer"],
        [Position = 73, TargetColumn = "Original Tanking Date", SourceList = "Order Items", SourceField = "OriginalTankingDate", Rule = "copy", Arg = null, Type = "datetext", Basis = "viewer"],
        [Position = 74, TargetColumn = "Estimated Delivery Date", SourceList = "Order Items", SourceField = "EstimatedDeliveryDate", Rule = "copy", Arg = null, Type = "datetext", Basis = "D3"],
        [Position = 75, TargetColumn = "Tanking date change justification", SourceList = "Order Items", SourceField = "TankingDateChangeJustification", Rule = "copy", Arg = null, Type = "text", Basis = "viewer"],
        [Position = 76, TargetColumn = "Manual Estimated Delivery Date", SourceList = "Order Items", SourceField = "ManualEstimatedDeliveryDate", Rule = "copy", Arg = null, Type = "datetext", Basis = "viewer"],
        [Position = 77, TargetColumn = "BO", SourceList = "Order Items", SourceField = "BO", Rule = "bo", Arg = null, Type = "text", Basis = "D2"],
        [Position = 78, TargetColumn = "Price Value", SourceList = "Order", SourceField = "Price", Rule = "copy", Arg = null, Type = "number", Basis = "viewer"],
        [Position = 79, TargetColumn = "Price CAD", SourceList = "Order Items", SourceField = "PriceCAD", Rule = "copy", Arg = null, Type = "number", Basis = "D3"],
        [Position = 80, TargetColumn = "Price USD", SourceList = "Order Items", SourceField = "PriceUSD", Rule = "copy", Arg = null, Type = "number", Basis = "D3"],
        [Position = 81, TargetColumn = "Navigation Order", SourceList = "computed", SourceField = "computed", Rule = "navorder", Arg = "Order", Type = "text", Basis = "recipe"],
        [Position = 82, TargetColumn = "Navigation Model", SourceList = "computed", SourceField = "computed", Rule = "navmodel", Arg = "PO Item #", Type = "text", Basis = "recipe"],
        [Position = 83, TargetColumn = "Archived", SourceList = "legacy", SourceField = "legacy", Rule = "legacy", Arg = null, Type = "text", Basis = "legacy"],
        [Position = 84, TargetColumn = "Lot", SourceList = "legacy", SourceField = "legacy", Rule = "legacy", Arg = null, Type = "text", Basis = "legacy"],
        [Position = 85, TargetColumn = "Tanking Date Status", SourceList = "legacy", SourceField = "legacy", Rule = "legacy", Arg = null, Type = "text", Basis = "legacy"],
        [Position = 86, TargetColumn = "Planning Notes", SourceList = "legacy", SourceField = "legacy", Rule = "legacy", Arg = null, Type = "text", Basis = "legacy"],
        [Position = 87, TargetColumn = "Production Complexity", SourceList = "legacy", SourceField = "legacy", Rule = "legacy", Arg = null, Type = "text", Basis = "legacy"],
        [Position = 88, TargetColumn = "__PowerAppsId__", SourceList = "legacy", SourceField = "legacy", Rule = "legacy", Arg = null, Type = "text", Basis = "legacy"],
        [Position = 89, TargetColumn = "Client Desired Date", SourceList = "legacy", SourceField = "legacy", Rule = "legacy", Arg = null, Type = "date", Basis = "legacy"],
        [Position = 90, TargetColumn = "FI", SourceList = "legacy", SourceField = "legacy", Rule = "legacy", Arg = null, Type = "text", Basis = "legacy"],
        [Position = 91, TargetColumn = "Stack", SourceList = "legacy", SourceField = "legacy", Rule = "legacy", Arg = null, Type = "text", Basis = "legacy"],
        [Position = 92, TargetColumn = "Production Status", SourceList = "legacy", SourceField = "legacy", Rule = "legacy", Arg = null, Type = "text", Basis = "legacy"],
        [Position = 93, TargetColumn = "Last Synchronisation Date", SourceList = "archive", SourceField = "archive", Rule = "archive", Arg = null, Type = "date", Basis = "archive"],
        [Position = 94, TargetColumn = "BO1 Part Numbre", SourceList = "Order Items", SourceField = "BO1PartNumber", Rule = "bo", Arg = null, Type = "text", Basis = "D2"],
        [Position = 95, TargetColumn = "BO1 Description", SourceList = "Order Items", SourceField = "BO1Description", Rule = "bo", Arg = null, Type = "text", Basis = "D2"],
        [Position = 96, TargetColumn = "BO1 PO Intern", SourceList = "Order Items", SourceField = "BO1POIntern", Rule = "bo", Arg = null, Type = "text", Basis = "D2"],
        [Position = 97, TargetColumn = "BO1 Date", SourceList = "Order Items", SourceField = "BO1Date", Rule = "bo", Arg = null, Type = "datetext", Basis = "D2"],
        [Position = 98, TargetColumn = "BO1 Fournisseur Interne", SourceList = "Order Items", SourceField = "BO1Fournisseur", Rule = "bo", Arg = null, Type = "text", Basis = "D2"],
        [Position = 99, TargetColumn = "BO1 OK", SourceList = "Order Items", SourceField = "BO1OK", Rule = "bo", Arg = null, Type = "logical", Basis = "D2"],
        [Position = 100, TargetColumn = "BO2 Part Numbre", SourceList = "Order Items", SourceField = "BO2PartNumber", Rule = "bo", Arg = null, Type = "text", Basis = "D2"],
        [Position = 101, TargetColumn = "BO2 Description", SourceList = "Order Items", SourceField = "BO2Description", Rule = "bo", Arg = null, Type = "text", Basis = "D2"],
        [Position = 102, TargetColumn = "BO2 PO Intern", SourceList = "Order Items", SourceField = "BO2POIntern", Rule = "bo", Arg = null, Type = "text", Basis = "D2"],
        [Position = 103, TargetColumn = "BO2 Date", SourceList = "Order Items", SourceField = "BO2Date", Rule = "bo", Arg = null, Type = "datetext", Basis = "D2"],
        [Position = 104, TargetColumn = "BO2 Fournisseur Interne", SourceList = "Order Items", SourceField = "BO2Fournisseur", Rule = "bo", Arg = null, Type = "text", Basis = "D2"],
        [Position = 105, TargetColumn = "BO2 OK", SourceList = "Order Items", SourceField = "BO2OK", Rule = "bo", Arg = null, Type = "logical", Basis = "D2"],
        [Position = 106, TargetColumn = "BO3 Part Numbre", SourceList = "Order Items", SourceField = "BO3PartNumber", Rule = "bo", Arg = null, Type = "text", Basis = "D2"],
        [Position = 107, TargetColumn = "BO3 Description", SourceList = "Order Items", SourceField = "BO3Description", Rule = "bo", Arg = null, Type = "text", Basis = "D2"],
        [Position = 108, TargetColumn = "BO3 PO Intern", SourceList = "Order Items", SourceField = "BO3POIntern", Rule = "bo", Arg = null, Type = "text", Basis = "D2"],
        [Position = 109, TargetColumn = "BO3 Date", SourceList = "Order Items", SourceField = "BO3Date", Rule = "bo", Arg = null, Type = "datetext", Basis = "D2"],
        [Position = 110, TargetColumn = "BO3 Fournisseur Interne", SourceList = "Order Items", SourceField = "BO3Fournisseur", Rule = "bo", Arg = null, Type = "text", Basis = "D2"],
        [Position = 111, TargetColumn = "BO3 OK", SourceList = "Order Items", SourceField = "BO3OK", Rule = "bo", Arg = null, Type = "logical", Basis = "D2"]
    }, type table [Position = Int64.Type, TargetColumn = text, SourceList = text, SourceField = text, Rule = text, Arg = nullable text, Type = text, Basis = text])
in
    Source
