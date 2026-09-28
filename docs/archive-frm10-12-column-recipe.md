# `TableArchiveFRM10_12`: column recipe (viewer route today → direct from SharePoint)

Researched 2026-09-28 from `FRM10-12/viewer/power-query/*.pq`, the 09-27 23:56 Archive active copy, and
the mirror's `Columns` catalog. This is the spec for the viewer-free `Archive FRM10-12` query
(plan: `~/.claude/plans/rerunning-the-dry-run-snug-lighthouse.md`, decisions D1–D6 and the source rule).

## How it's built today
`Archive FRM10-12.pq` → `TrackRemoteTable("FRM10-12","TableOrders",…,"Order")` → `ImportFromIndex` →
viewer workbook `TableOrders` (82 columns: 76 query + 6 Excel formula) → accumulate (identical to
`AccumulateIntoLocal.pq`) → `EnforceFormats` (a no-op: `TableFormatParser` Enforced = Display = ".").
Column order = the 82 source columns, then the local-only columns (10 legacy, then `Last Synchronisation Date`) = 93.

🔑 **Types come from the load path.** The table loads through the **Data Model**
(`ModelConnection_ExternalData_1`). `Table.Combine` with the local table (`Excel.CurrentWorkbook`) makes
every column type `any`, so values land as text: dates as `"m/d/yyyy h:mm:ss AM"`, numbers as invariant
text. The refresher's step 8 turns them back into dates and booleans. **The new query must end with an explicit
`Table.TransformColumnTypes` over the pinned columns** so the values arrive typed. Keep the same query name
and the same load, and never recreate the table: the Nightly Sync reads it by id `{17014A43-…}`.

## Sources (source rule: parent data from the parent list, joined by lookup id)
- **OI** = Order Items (the unit's own fields only). **ORD** = Order via OI `OrderNumberId` → `Id`.
  **MR** = Model Revisions via OI `ModelRevisionId` → `Id`. **CLI** = Clients via ORD `ClientId`.
- ❌ Never OI's sync copies (`Ord*`, `Rev*`, `Mdl*`, `Cli*`, "Order - …") or `*_TextField` mirrors. The
  mirror's `Columns.csv` marks them with `syncedFromList`.

## The columns, in order
Today's archive cell type is in brackets. "→ date/number" marks where the new query is **cleaner** (allowed: same name, same data, better type).

| # | Column | Source (internal name) | Rule |
|--|--|--|--|
|1|Order|OI `Title`|key; drop null/"" Title; loud error on duplicates|
|2|Client|ORD `Client` → CLI `Title`|display text|
|3|KVA and KV|MR `kVA_x0020_and_x0020_kV`|today fr-CA text `24,9`; cleaner: number|
|4|Primary Voltage|MR `PrimaryVoltage`|number (empty today)|
|5|Secondary Voltage|MR `SecondaryVoltage`|number (empty today)|
|6|Phases|MR `Phases`|[text "3"] → number|
|7|JS #|MR `JS_x0020__x0023_`|text|
|8|Description|MR `Description` (multi-choice)|`Text.Combine(values, ", ")`|
|9|Type|MR `Model_x0020_Type`|text|
|10|PO|ORD `PO`|text|
|11|Order Date|ORD `Order_x0020_Date`|date-only → first 10 chars|
|12|Lead Time|CLI `CliLeadTimeWeeks` (D3)|null → 26; number. Today it's FRM13 `LeedTime` (three clients are spelled differently there, so they got 26)|
|13|Ing. Due Date|computed|`(OI TankingDate ?? ORD Initial Promised Date) − (LeadTime+4)×7` days; `try … otherwise null`|
|14|Qty|OI `Qty`|number|
|15|PO Item #|MR `ModelName`|text|
|16|Family|MR `Family`|text|
|17|Duplicate|— (legacy)|null|
|18|Engineering Required|ORD `EngineeringRequired`|true → "Y", else null|
|19|Duplicate Order|— (legacy)|null|
|20|Price|ORD `Price`|number; blank → 0 (today HYPERLINK text from a viewer formula)|
|21|Province/State|ORD `Province_x002F_State`|text|
|22|WET-WETP|ORD `WET_x002d_WETP`|text|
|23|Indexing|ORD `Indexing`|text|
|24|LDs|ORD `LDs`|true → "Y", else null|
|25|Initial Promised Date|ORD `Initial_x0020_Promised_x0020_Dat`|date-only|
|26|Trimestrial Customer|OI `TrimestrialCustomer`|text|
|27|Client Date Status|ORD `ClientDateStatus`|text|
|28|Info+|OI `Info_x002b_`|text|
|29|Protector Status|OI `ProtectorStatus`|text|
|30|Protector & Switchgear PO|OI `ProtectorSwitchgearPO`|text|
|31|Protector & Switchgear Item #|OI `Protector_x0020__x0026__x0020_Sw`|text|
|32|Sales Notes|ORD `SalesNotes`|text|
|33|Technical Notes|OI `Technical_x0020_Notes`|text (raw rich-text HTML today; strip-to-text is a cleaning option for review)|
|34|Location|OI `Location`|name → 2-letter code via `LocationCodes` (12 pairs); unmapped passes through|
|35|Status|computed|`StatusStampCodes(step, StepStatus) & "-" & month-code(StatusDate) & "-" & day`; falls back to OI `Status` when either half is missing|
|36|Witness/Other|OI `Witness_x002f_Other`|text|
|37–41|Temperature Rise, Impulse, DB, Partial D, Oil Analysis|OI `TemperatureRise`, `Impulse`, `DB`, `PartialD`, `OilAnalysis`|true → "x", else null (never false)|
|42|SFRA|OI `SFRA`|true → "Y", else null|
|43|CSA|OI `CSA`|boolean|
|44|Core|MR `Core_x0020_Type`|text|
|45|Core Status|OI `CoreStatus`|text|
|46|Oil Type|MR `Oil_x0020_Type`|text|
|47|Oil Amount|MR `OilAmount`|number|
|48|Production Line|OI `ProductionLine`|text|
|49|Configuration|OI `Configuration`|text|
|50|Section Qty|OI `Section_x0020_Qty`|number|
|51|Cable|MR `Cable`|text|
|52|Coil Winder|OI `CoilWinder`|text|
|53–55|Form, Copper (LV), Wire (HV)|MR `Form`, `Copper_x0028_LV_x0029_`, `Wire_x0028_HV_x0029_`|text|
|56|Overcoil|MR `Overcoil`|today fr-CA text `31,75`; cleaner: number|
|57|Winder|OI `Winder`|text|
|58|Time (days)|OI `Time_x0028_days_x0029_`|number|
|59|Tank|OI `Tank`|true → "R", else null|
|60|Tank Delivery Date|OI `TankDeliveryDate`|date-only|
|61|Frame|OI `Frame`|text|
|62–64|ISO Stack, ISO Coil, Lead Assembly|OI `ISOStack`, `ISOCoil`, `LeadAssembly`|true → "R", else null|
|65–68, 70, 71|Coiling / Stacking / Assembly / Drying / Testing / Finishing Date|OI `CoilingDate`, `StackingDate`, `AssemblyDate`, `DryingDate`, `TestingDate`, `FinishingDate` (display "… End Date")|**"EC"** if `<Stage>Status` = "In Progress" (even with no date), else the date-only value|
|69|Tanking Date|OI `Planned_x0020_Tanking_x0020_Date`|date-only (**planned**)|
|72|Delivery Date|OI `Planned_x0020_Delivery_x0020_Dat`|date-only (**planned**). The Nightly Sync gate reads this plus `Location = 'LI'`|
|73|Original Tanking Date|OI `OriginalTankingDate`|date-only|
|74|Estimated Delivery Date|OI `EstimatedDeliveryDate` (calculated, D3)|date (today a viewer Excel formula)|
|75|Tanking date change justification|OI `TankingDateChangeJustification` (display "Planning Notes")|text. ⚠️ SharePoint's "Planning Notes" maps here, **not** to column 86|
|76|Manual Estimated Delivery Date|OI `ManualEstimatedDeliveryDate`|date-only|
|77|BO|OI `BO` (D2)|text; historical blanks from `TableArchiveBO[BO]`|
|78|Price Value|ORD `Price`|number|
|79|Price CAD|OI `PriceCAD` (calculated, D3)|number|
|80|Price USD|OI `PriceUSD` (calculated, D3)|number|
|81|Navigation Order|computed|`"Ouvrir commande " & Text.BeforeDelimiter(Order,"-")`; null if Order has no "-"|
|82|Navigation Model|computed|`"Ouvrir modèle " & PO Item #`|
|83–92|Archived, Lot, Tanking Date Status, Planning Notes, Production Complexity, `__PowerAppsId__`, Client Desired Date, FI, Stack, Production Status|— (legacy, never produced)|kept as they are for old rows; null for new rows|
|93|Last Synchronisation Date|archive-side|today on every row SharePoint still sends; kept for rows that left|
|94+|**BO detail (D2)**: `TableArchiveBO`'s BO1–BO3 columns, exact header names|OI `BO1PartNumber`, `BO1Description`, `BO1POIntern`, `BO1Date`, `BO1Fournisseur`, `BO1OK` (and BO2, BO3)|OI value if non-blank, else `TableArchiveBO`'s; both non-blank and different → conflict list|

## Traps
- Map by **internal name**, never display name (column 75 vs 86 "Planning Notes").
- The six E7 orders (22140/41/56/57, P00005, P10003) are stored at `T00:00Z`. First-10-chars gives the stored date. The viewer showed a day earlier. This is an **intended** difference.
- `Ing. Due Date` reads OI `TankingDate` (the actual end date), not Planned Tanking Date, as today.
- "" versus null: today's text columns mix both. The new query normalises blanks to null (cleaner); the checker treats "" = null.
- D4: no "already archived" self-filter. Rows that leave SharePoint are kept by `AccumulateIntoLocal`.
