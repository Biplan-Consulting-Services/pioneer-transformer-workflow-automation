# `Order Items` view spec — `FRM10-12 Layout`

A read-only-by-convention view on **`Order Items`** whose column order mirrors FRM10-12's
**`TableOrders`** left to right, so staff moving from the workbook to the list find the same
layout. Authored 2026-09-08. **Nothing in here has been executed** — the creation script is
`scripts/create_frm1012_view.js`, and it is meant to be pasted into a browser console by hand.

| | |
|---|---|
| Site | `https://ermcopower.sharepoint.com/sites/PioneerPlanificatio` |
| List | `Order Items` — `d6468ec5-c7b5-44a3-8ce0-f81f059b671d` |
| View name | `FRM10-12 Layout` |
| ViewFields | **79** (73 mirrored + 6 list-native tail) |
| Filter / sort | **none** — deliberately. See *Why no filter* below. |
| Source of column order | `FRM10-12/live-workbook-data/FRM10-12_2026-09-04_23h08m.xlsx`, sheet `Orders`, table `TableOrders`, ref `B5:CE1024`, header row 5, 82 columns |

## The count, up front

| Kind | Count | Meaning |
|---|---:|---|
| direct | 34 | Same concept, native `Order Items` column, same display name. |
| renamed | 10 | Same concept, native column, different name. |
| parent-sync | 28 | Now an `Ord*` / `Mdl*` / `Rev*` column in the `Parent Sync` group. |
| split | 1 | The composite `Status`. |
| absent | 3 | In the workbook, not on the list. No name invented. |
| excluded | 6 | The six native Excel formula columns. |
| **total** | **82** | |

**73 of the 82 land in the view.** Nothing is `UNRESOLVED`: every internal name below came out
of the `ListSchema` record of `sharepoint-lists/Order Items 2026-09-05 1432.csv`, out of
`sharepoint-lists/N2 field definitions 2026-09-05.json`, or off the hand-resolved lookup list
(2026-09-07). The generator that produced this doc **refuses to emit** a name it cannot find in
one of those three.

### 🔴 Read this before showing the view to anyone

**36 of the 79 columns will render completely blank**, and that is expected, not a bug:

- **28 parent-sync columns** (`Ord*` / `Mdl*` / `Rev*`) were created empty on 2026-09-07.
  The N3 sync flows that fill them are **not built yet** (they wait on A3). Until then this view
  looks like the workbook with its whole model/order-spec block cut out.
- **4 native columns were never backfilled** from the workbook, though the columns exist:
  `Configuration` (465 workbook rows have a value, 0 list rows do), `Section_x0020_Qty` (112),
  `Info_x002b_` (96), `Technical_x0020_Notes` (6). All four come from the `Models` list in
  `ColumnMap.pq` and none appears in the transfer flow's field mapping — this looks like a
  **genuine backfill gap**, not a naming difference.
- **4 more are blank on both sides**, so nothing is lost: `ProtectorStatus`,
  `ProtectorSwitchgearPO`, `Protector_x0020__x0026__x0020_Sw`, `Time_x0028_days_x0029_`.
- And `RevDuplicateOrder` is expected to stay empty by design (N2 **KEEP**).

If the point of the view is staff recognition on day one, consider shipping it *after* N3, or
shipping it now and telling people the blank block is the not-yet-synced part.

## The mapping, in `TableOrders` order

`#` is the workbook's column position (1 = leftmost, column `B`).
`—` in the internal-name column means the column is not in the view.

| # | FRM10-12 `TableOrders` | Kind | `Order Items` internal name | Type | Src | Notes |
|--:|---|---|---|---|:-:|---|
| 1 | `Order` | renamed | `Title`<br>*(display: Unit ID)* | Text | S2 | `Title` is the renamed built-in. Holds the unit ID verbatim, ` SA` suffix included (1052/1052 populated); it is the join key this whole mapping was verified through. |
| 2 | `Client` | direct | `Client` | Lookup -> Clients | S4 | Now a Lookup to `Clients`. 948/948 joined rows agree with the workbook. |
| 3 | `KVA and KV` | parent-sync | `RevkVA`<br>*(display: Mod. Rev. - kVA)* | Number | S3 | `ColumnMap.pq`: workbook `KVA and KV` comes from `Model Revisions.kVA`. Same field, shorter name -- it is not a kVA+kV composite. |
| 4 | `Primary Voltage` | parent-sync | `RevPrimaryVoltage`<br>*(display: Mod. Rev. - Primary Voltage)* | Number | S3 |  |
| 5 | `Secondary Voltage` | parent-sync | `RevSecondaryVoltage`<br>*(display: Mod. Rev. - Secondary Voltage)* | Number | S3 |  |
| 6 | `Phases` | parent-sync | `RevPhases`<br>*(display: Mod. Rev. - Phases)* | Number | S3 |  |
| 7 | `JS #` | parent-sync | `RevJS`<br>*(display: Mod. Rev. - JS #)* | Text | S3 |  |
| 8 | `Description` | parent-sync | `RevModelDescription`<br>*(display: Mod. Rev. - Model Description)* | Note | S3 | `ColumnMap.pq`: workbook `Description` comes from `Model Revisions.Model Description`, a multi-choice field the workbook flattens to a comma-joined string. The synced column is Note. |
| 9 | `Type` | parent-sync | `RevModelType`<br>*(display: Mod. Rev. - Model Type)* | Text | S3 | `ColumnMap.pq`: workbook `Type` comes from `Model Revisions.Model Type`. |
| 10 | `PO` | parent-sync | `OrdPO`<br>*(display: Order - PO)* | Text | S3 |  |
| 11 | `Order Date` | parent-sync | `OrdOrderDate`<br>*(display: Order - Order Date)* | DateTime | S3 | Created DateOnly on purpose (N2 remap) -- DateTime reintroduces the UTC-midnight bug. |
| 12 | `Lead Time` | **absent** | — |  |  | **No counterpart, by decision.** N2 marked `Order - Lead Time` **REPLACE**: the real lead time comes from FRM13's `LeedTime` via `Clients.Lead Time`, and `Order.Lead Time` disagrees on 306 of 342 orders. The workbook does not store it either -- `TableOrders.pq` drops the column and re-derives it from `ClientLeadTimes` every refresh. |
| 13 | `Ing. Due Date` | **absent** | — |  |  | **No counterpart.** Derived inside `TableOrders.pq` (`baseDate - (Lead Time + 4) x 7 days`), never stored. Cannot be shown until either that formula or `Lead Time` itself lands on the list. |
| 14 | `Qty` | direct | `Qty` | Number | S2 | Number on the list, text in the workbook (`ColumnMap.pq` keeps it text deliberately). 938/948 agree; the 10 are formatting. |
| 15 | `PO Item #` | renamed | `Model`<br>*(display: Model)* | Lookup -> Models | S4 | The `Model` lookup **displays `Models.Model_Code`**, which is exactly this column -- verified on data: 943 of 948 joined rows agree. Do **not** reach for `Model_ID_TextField` / `MdlModelID`: those hold `Model_ID` (`M-GEPO-0009`), a different identifier that matches `Model_Code` on only 4 of 390 models. |
| 16 | `Family` | parent-sync | `RevFamily`<br>*(display: Mod. Rev. - Family)* | Text | S3 |  |
| 17 | `Duplicate` | **absent** | — |  |  | **Deliberately not migrated.** Superseded by the `EngineeringChangeOrders` / `ModelChanges` trackers (`infrastructure-overview.md`); the transfer-flow spec excludes it by name. |
| 18 | `Engineering Required` | parent-sync | `OrdEngineeringRequired`<br>*(display: Order - Engineering Required)* | Boolean | S3 | Boolean on the list, `Y`/`N` text in the workbook. One live row reads `indeterrmine` (typo) and maps to blank, not `No`. |
| 19 | `Duplicate Order` | parent-sync | `RevDuplicateOrder`<br>*(display: Mod. Rev. - Duplicate Order)* | Text | S3 | N2 **KEEP**: created, but expected to stay empty (0 of 391 `Model Revisions` rows populated). Will render blank indefinitely. |
| 20 | `Price` | excluded | — |  |  | **Native Excel formula column** -- `=HYPERLINK(<Order list URL>, [Price Value])`. It is `Price Value` wearing a link, not a separate fact. Use `OrdPrice` at position 78. |
| 21 | `Province/State` | parent-sync | `OrdProvinceState`<br>*(display: Order - Province/State)* | Text | S3 |  |
| 22 | `WET-WETP` | parent-sync | `OrdWETWETP`<br>*(display: Order - WET-WETP)* | Text | S3 |  |
| 23 | `Indexing` | parent-sync | `OrdIndexing`<br>*(display: Order - Indexing)* | Text | S3 |  |
| 24 | `LDs` | parent-sync | `OrdLDs`<br>*(display: Order - LDs)* | Boolean | S3 | Boolean on the list; clean `Y`/`N` in the workbook (167/38). |
| 25 | `Initial Promised Date` | parent-sync | `OrdInitialPromisedDate`<br>*(display: Order - Initial Promised Date)* | DateTime | S3 |  |
| 26 | `Trimestrial Customer` | direct | `TrimestrialCustomer` | Choice | S2 | 156 list rows populated; 116/116 of the joined non-blanks agree. Stays Text pending the `Penalite Trimestrielle` clarification. |
| 27 | `Client Date Status` | parent-sync | `OrdClientDateStatus`<br>*(display: Order - Client Date Status)* | Text | S3 | Needs normalising on sync -- `CONFIRMED `, `CONFRIMED`, `Confirmed` all mean one thing in the source data. |
| 28 | `Info+` | direct | `Info_x002b_` | Text | S2 | `+` is encoded. **Column exists, data does not** -- 96 workbook rows carry a value, 0 of 1052 list rows do. |
| 29 | `Protector Status` | direct | `ProtectorStatus` | Choice | S2 | Choice. 0 populated on either side, so nothing has ever validated against its option list. |
| 30 | `Protector & Switchgear PO` | direct | `ProtectorSwitchgearPO` | Text | S2 | Internal name is **not** escaped -- this one was created from a short name and renamed. 0 populated on either side. |
| 31 | `Protector & Switchgear Item #` | direct | `Protector_x0020__x0026__x0020_Sw` | Text | S2 | The canonical trap on this list: escaped **and truncated at 32 characters**, stopping mid-word inside `Sw`. Never retype it. 0 populated on either side. |
| 32 | `Sales Notes` | parent-sync | `OrdSalesNotes`<br>*(display: Order - Sales Notes)* | Note | S3 |  |
| 33 | `Technical Notes` | direct | `Technical_x0020_Notes` | Note | S2 | `ColumnMap.pq`: workbook `Technical Notes` comes from `Models.Notes`. **Column exists, data does not** -- 6 workbook rows populated, 0 on the list. Not the same field as `RevNotes` (`Model Revisions.Notes`). |
| 34 | `Location` | direct | `Location` | Choice | S2 | Same concept, **different value domain**: the workbook stores 2-letter codes (`TA`, `XT`, `FO`), the list stores full names (`Tanking`, `Exterieur`, `Four`). 0 of 948 joined rows agree textually and that is correct, not a mismatch. `AN` (Annulee) maps to no Location value at all -- it became `Item Status = Cancelled`. |
| 35 | `Status` | **split** | `Status` | Text | S2 | **The split.** `Status` is a composite -- a step code plus a month/day suffix (`TE-Se-4`) -- and the transfer flow copies it across verbatim, so this *is* today's counterpart: 12/12 of the joined non-blanks agree. But the list also carries the decomposed model: `ItemStatus` (lifecycle) plus 8 x `{Stage} Status` / `{Stage} Start Date` / `{Stage} End Date` triples. Roadmap item 18 splits the composite into `Step Status` + `Status Date`; when that lands, this row needs revisiting. Only 211 of 1052 list rows have any `Status`. |
| 36 | `Witness/Other` | direct | `Witness_x002f_Other` | Text | S2 | `/` is encoded. |
| 37 | `Temperature Rise` | direct | `TemperatureRise` | Boolean | S2 | Boolean on the list; the workbook uses non-blank `x` to mean yes. |
| 38 | `Impulse` | direct | `Impulse` | Boolean | S2 |  |
| 39 | `DB` | direct | `DB` | Boolean | S2 |  |
| 40 | `Partial D` | direct | `PartialD` | Boolean | S2 |  |
| 41 | `Oil Analysis` | direct | `OilAnalysis` | Boolean | S2 |  |
| 42 | `SFRA` | direct | `SFRA` | Boolean | S2 | The workbook marks this one `Y`, not `x`; mapped on non-blank, so it survives. |
| 43 | `CSA` | direct | `CSA` | Boolean | S2 |  |
| 44 | `Core` | parent-sync | `RevCoreType`<br>*(display: Mod. Rev. - Core Type)* | Text | S3 | `ColumnMap.pq`: workbook `Core` comes from `Model Revisions.Core Type`. |
| 45 | `Core Status` | direct | `CoreStatus` | Choice | S2 | Choice; the workbook already stores the display value, so no code table. 180/222 of the joined non-blanks agree. |
| 46 | `Oil Type` | parent-sync | `RevOilType`<br>*(display: Mod. Rev. - Oil Type)* | Text | S3 |  |
| 47 | `Oil Amount` | parent-sync | `RevOilAmount`<br>*(display: Mod. Rev. - Oil Amount)* | Number | S3 |  |
| 48 | `Production Line` | direct | `ProductionLine` | Choice | S2 | 838/851 of the joined non-blanks agree. |
| 49 | `Configuration` | direct | `Configuration` | Text | S2 | `ColumnMap.pq`: workbook `Configuration` comes from `Models.Configuration`. **Column exists, data does not** -- 465 workbook rows populated, 0 on the list. The single largest gap in this mapping. |
| 50 | `Section Qty` | direct | `Section_x0020_Qty` | Number | S2 | From `Models` too. **Column exists, data does not** -- 112 workbook rows populated, 0 on the list. |
| 51 | `Cable` | parent-sync | `RevCable`<br>*(display: Mod. Rev. - Cable)* | Text | S3 |  |
| 52 | `Coil Winder` | direct | `CoilWinder` | Text | S2 | Text on purpose -- values mix IDs and ranges like `100-104`. 134/188 of the joined non-blanks agree. |
| 53 | `Form` | parent-sync | `RevForm`<br>*(display: Mod. Rev. - Form)* | Text | S3 |  |
| 54 | `Copper (LV)` | parent-sync | `RevCopperLV`<br>*(display: Mod. Rev. - Copper (LV))* | Text | S3 |  |
| 55 | `Wire (HV)` | parent-sync | `RevWireHV`<br>*(display: Mod. Rev. - Wire (HV))* | Text | S3 |  |
| 56 | `Overcoil` | parent-sync | `RevOvercoil`<br>*(display: Mod. Rev. - Overcoil)* | Number | S3 | Created Number, though `ColumnMap.pq` types the workbook column as text. |
| 57 | `Winder` | direct | `Winder` | Text | S2 | 777/794 of the joined non-blanks agree. |
| 58 | `Time (days)` | direct | `Time_x0028_days_x0029_` | Number | S2 | Parentheses encoded. 0 populated on either side. |
| 59 | `Tank` | direct | `Tank` | Boolean | S2 | Boolean on the list. Not a tank number and not FRM11's join key -- FRM11 keys on `NUMERO DE CUVE`, which is the unit ID. |
| 60 | `Tank Delivery Date` | direct | `TankDeliveryDate` | DateTime | S2 | 55/55 of the joined non-blanks agree. |
| 61 | `Frame` | direct | `Frame` | Choice | S2 | Choice; the workbook already stores the display value. 254/303 of the joined non-blanks agree. |
| 62 | `ISO Stack` | direct | `ISOStack` | Boolean | S2 | Boolean. |
| 63 | `ISO Coil` | direct | `ISOCoil` | Boolean | S2 | Boolean. |
| 64 | `Lead Assembly` | direct | `LeadAssembly` | Boolean | S2 | Boolean. |
| 65 | `Coiling Date` | renamed | `CoilingDate`<br>*(display: Coiling End Date)* | DateTime | S2 | Display name is **Coiling End Date**; the internal name kept the short form. 116/116 agree. |
| 66 | `Stacking Date` | renamed | `StackingDate`<br>*(display: Stacking End Date)* | DateTime | S2 | Display **Stacking End Date**. 73/73 agree. |
| 67 | `Assembly Date` | renamed | `AssemblyDate`<br>*(display: Assembly End Date)* | DateTime | S2 | Display **Assembly End Date**. 65/65 agree. |
| 68 | `Drying Date` | renamed | `DryingDate`<br>*(display: Drying End Date)* | DateTime | S2 | Display **Drying End Date**. 52/54 agree. |
| 69 | `Tanking Date` | renamed | `Planned_x0020_Tanking_x0020_Date`<br>*(display: Planned Tanking Date)* | DateTime | S2 | **Deliberately not `TankingDate`.** Correction of 2026-08-21: the workbook's `Tanking Date` is a *planning* date, not a completion date. Internal name truncated at 32 chars. 832/852 agree. `TankingDate` (`Tanking End Date`) still holds 881 values written by the earlier wrong mapping and is pending remediation -- putting it in this view would display fabricated completions. |
| 70 | `Testing Date` | renamed | `TestingDate`<br>*(display: Testing End Date)* | DateTime | S2 | Display **Testing End Date**. 16/17 agree. |
| 71 | `Finishing Date` | renamed | `FinishingDate`<br>*(display: Finishing End Date)* | DateTime | S2 | Display **Finishing End Date**. 12/12 agree. |
| 72 | `Delivery Date` | renamed | `Planned_x0020_Delivery_x0020_Dat`<br>*(display: Planned Delivery Date)* | DateTime | S2 | Same correction as `Tanking Date`, and the same 32-char truncation -- note the missing `e` in `Dat`. 262/271 agree. `DeliveryDate` (`Delivery End Date`) likewise holds 299 values from the old mapping, pending the same remediation. |
| 73 | `Original Tanking Date` | direct | `OriginalTankingDate` | DateTime | S2 | 868/868 agree. |
| 74 | `Tanking date change justification` | direct | `TankingDateChangeJustification`<br>*(display: Tanking Date Change Justification)* | Note | S2 | Note field; only the display name changed case. 185/211 agree. |
| 75 | `Estimated Delivery Date` | excluded | — |  |  | **Native Excel formula column** -- an 8-branch cascade over `Delivery Date`, `Manual Estimated Delivery Date`, the stage dates, and `Order Date + 90 + FRM13 lead time`. No counterpart on `Order Items`: the `Order` list has `Estimated_x0020_Delivery_x0020_D`, but N2 created no `Ord*` sync column for it, so there is nothing a view could show. Open roadmap workstream (`calculated-columns-plan.md`). |
| 76 | `Manual Estimated Delivery Date` | direct | `ManualEstimatedDeliveryDate` | DateTime | S2 | 114/114 agree. Already the sort key of the `Production Floor` view. |
| 77 | `BO` | direct | `BO` | Choice | S2 | Choice (`BO`/`OK`). 54/66 of the joined non-blanks agree. In the workbook it is joined in from the BO Manager workbook; on the list it is a stored value with 19 `BO1..BO3` detail columns behind it. |
| 78 | `Price Value` | parent-sync | `OrdPrice`<br>*(display: Order - Price)* | Currency | S3 | `ColumnMap.pq`: workbook `Price Value` comes from `Order.Price`. Created as Currency. |
| 79 | `Price CAD` | excluded | — |  |  | **Native Excel formula column** -- `Price Value` times a year-keyed FX rate from `Table_USD_CAD_Conversion_Rate`, selected by `Province/State`. Neither the rate table nor the formula exists on the list; `Order` has `Price_x0020_CAD` but no `Ord*` sync column. |
| 80 | `Price USD` | excluded | — |  |  | **Native Excel formula column**, the mirror of `Price CAD`. Same reason. |
| 81 | `Navigation Order` | excluded | — |  |  | **Native Excel formula column** -- `=HYPERLINK(<Order list filtered by order number>, "Navigate to Order ...")`. Redundant on a SharePoint list: the `Order Number` lookup *is* that link. Carried in the tail below instead. |
| 82 | `Navigation Model` | excluded | — |  |  | **Native Excel formula column** -- the same hyperlink trick pointing at `Models Revisions`. Superseded by the `Model` and `Model Revision` lookups, which both render as links to the parent item. |

### Tail — 6 list-native columns, appended after the mirror

These have no `TableOrders` counterpart. They go **after** all 73 mirrored fields so the mirror
stays intact from position 1; the alternative (identity fields first, the way the list's own
`All Items` view does it) breaks the recognition the view exists for.

| `Order Items` internal name | Display | Type | Src | Why it is here |
|---|---|---|:-:|---|
| `OrderNumber` | Order Number | Lookup -> Order | S4 | Stands in for `Navigation Order` (position 81) -- the lookup renders as a link to the parent `Order` item. In the workbook the order number exists only as the text before the first `-` in `Order`. |
| `Unit_x0023_` | Unit # | Number | S2 | The `1` in `21408-1/1`. The workbook keeps it only inside the composite `Order` string. |
| `SAJob` | SA Job | Boolean | S2 | The ` SA` suffix promoted to a real flag; 43 workbook rows carry it inside the text. |
| `ItemStatus` | Item Status | Choice | S2 | The lifecycle axis the workbook never had -- `Active` / `Delivered` / `Cancelled` / `Regrouped`. It replaced `Location = AN`, and it is why every existing view filters on it. Without it this view shows cancelled and delivered units mixed into the floor. |
| `ModelRevision` | Model Revision | Lookup -> Model Revisions | S4 | Stands in for `Navigation Model` (position 82). The revision actually built for this unit -- distinct from `MdlLatestModelRevision`, which is the newest design (N2's KEEP note: different facts). |
| `RegroupedInto` | Regrouped Into | Lookup -> Order Items (multi) | S4 | Multi-value self-lookup, populated only when `Item Status = Regrouped`. No workbook equivalent; the old `GR` code is untraceable and unused. |

## Source legend

| Src | Where the internal name came from | Why it is trustworthy |
|:-:|---|---|
| S2 | The `ListSchema={...}` record at the head of `sharepoint-lists/Order Items 2026-09-05 1432.csv` — 90 `<Field>` tags, 87 real + 3 `Computed`. | SharePoint's own schema XML, verbatim. |
| S3 | `sharepoint-lists/N2 field definitions 2026-09-05.json` — the 48 `Parent Sync` columns created 2026-09-07. | The `Name` attribute the create script actually posted, with `Options: 8`, and read back afterwards: all 48 honoured exactly, no truncation. |
| S4 | Hand-resolved 2026-09-07 from list settings → the column → the `Field=` parameter in the URL. | The only route that works: a CSV export omits Lookup columns entirely — values *and* schema — and the `/fields` collection query hangs on this tenant. |

Two names in the schema are worth staring at, because a guess would read and write nothing
without erroring:

```
Protector & Switchgear Item #   ->  Protector_x0020__x0026__x0020_Sw   escaped, then cut mid-word at 32 chars
Planned Delivery Date           ->  Planned_x0020_Delivery_x0020_Dat   cut at 32 chars, losing the final 'e'
Planned Tanking Date            ->  Planned_x0020_Tanking_x0020_Date   exactly 32 chars, survives intact
Coiling End Date                ->  CoilingDate                        'End' dropped; same for Stacking/Assembly/
                                                                       Drying/Tanking/Testing/Finishing/Delivery
Unit ID                         ->  Title                              renamed built-in
```

## Judgement calls the user should review

1. **`Tanking Date` → `Planned_x0020_Tanking_x0020_Date`, not `TankingDate`** (and the same for
   `Delivery Date`). This follows the 2026-08-21 correction: the workbook's `Tanking Date` /
   `Delivery Date` are planning dates, not completions. Both `TankingDate` (881 values) and
   `DeliveryDate` (299 values) are still polluted by the earlier wrong mapping and awaiting
   remediation, so they are kept **out** of this view on purpose. On the data, the workbook
   column agrees with *both* targets (832/852 planned, 861/881 end) — which is exactly what a
   double-write looks like. **If the remediation runs before this view ships, revisit.**
2. **`PO Item #` → the `Model` lookup, not a text field.** Verified on data (943/948), but it
   means the column renders as a link rather than plain text, and it counts against the
   12-lookup view threshold.
3. **The tail goes last.** Puts `ItemStatus` at position 79 rather than near the front, which
   is unusual for this list — every other view leads with it or filters on it.
4. **No filter and no sort.** See below.
5. **`Status` stays as the composite.** It is the honest counterpart today, but roadmap item 18
   plans to split it, and the list already carries a fuller 8-stage model this view does not
   show. A future `FRM10-12 Layout` may need the 8 `{Stage} Status` columns inserted beside
   their dates instead.
6. **`Navigation Order` / `Navigation Model` are dropped rather than rebuilt.** The lookups
   already link to the same two lists. If staff genuinely use those cells as buttons, the
   nearest real equivalent is `OrdOrderFolder` (`Order - Order Folder`, a URL column) — but
   that points at the order's document folder, not the list item, so it is a different link.

### Why no filter and no sort

`TableOrders` is already filtered upstream: `TableOrders.pq` drops any row the Archive workbook
shows as `Location = AN`, or `LI` with a delivery date. So the workbook's ~1,000 rows are
*already* "active only". The list keeps cancelled/delivered rows until the reconciliation pass
deletes them, so a faithful mirror would want `ItemStatus eq 'Active'`.

It is left out anyway, for one reason: **this view's job is to prove the column mapping**, and a
filter hides rows that would otherwise reveal a bad mapping. Add the filter once the layout is
confirmed — the CAML is in the script, commented out, so it is a two-character edit.

`RowLimit` is set to **100**, matching `Production Floor` and `Planning`, not the default view's 30.

## Does a SharePoint view have a field limit? Yes — but not the one you would expect

**There is no documented maximum number of `ViewFields` in a SharePoint Online view.** The two
limits that are real and enforced:

1. **The lookup column threshold: 12 per view.** It counts Lookup, Person/Group and Managed
   Metadata columns together (including `Created By` / `Modified By` if shown). Exceeding it
   fails the whole view at render time with *"the number of lookup and workflow status columns
   it contains exceeds the threshold (12) enforced by the administrator"* — and on SharePoint
   Online it **cannot be raised**.
   **This view uses 5 of 12**: `Client`, `Model`, `OrderNumber`, `ModelRevision`, `RegroupedInto`.
   Comfortable, but it is the constraint to watch: adding `Created By`, `Modified By` and a
   couple more lookups would reach it.
2. **The list view threshold: 5,000 items.** Not a factor — `Order Items` holds 1,052.

So **79 ViewFields is fine**, and there is direct proof on this very list rather than an
assumption: the default `All Items` view already carries **95** fields, and its CSV export
renders all 95 columns. 82 mirrored columns were never at risk.

The real cost of a wide view is rendering, not a limit: the modern grid virtualises rows but not
columns, so ~79 columns means a lot of horizontal scrolling. That is inherent to the goal — the
workbook is that wide too.

Sources: [lookup column threshold (12), SharePoint Online](https://learn.microsoft.com/en-us/answers/questions/5334600/sharepoint-the-query-cannot-be-completed-because-t) ·
[the render-time error text](https://learn.microsoft.com/en-us/archive/msdn-technet-forums/ec14cda5-3e3a-4749-af5f-ba714ce2fa92) ·
[List View Threshold](https://support.microsoft.com/en-us/office/working-with-the-list-view-threshold-limit-for-all-versions-of-sharepoint-4a40bbdc-c5f8-4bbd-b9b6-745daf71c132)

## Endpoint facts this script relies on

Established by testing on this tenant (see `docs/n2-column-build-sheet.md`). Do not deviate:

| endpoint | works? |
|---|---|
| `POST _api/contextinfo` → `X-RequestDigest` | ✅ |
| `POST _api/web/lists/getbytitle('Order Items')/views` | ✅ (the create call) |
| `_api/web/lists/…/views/getbytitle('X')?$expand=ViewFields` | ✅ (the read-back) |
| `_api/web/lists/…/defaultview/viewfields` | ✅ |
| `_api/web/lists/…/fields/getbyinternalnameortitle('X')` | ✅ single field |
| `_api/v2.0/sites/root/lists/<id>/columns` | ✅ column metadata — `sites/root` is required |
| `_api/v2.0/lists/<id>/columns` | ❌ `itemNotFound` |
| `_api/web/lists/…/fields?$select=…&$filter=…` | ❌ **hangs / `Failed to fetch`** — never use it |

⚠️ Do not run the script from a SharePoint application page (`Home.aspx`): a batch run there
froze the renderer mid-request with the write outcome unknown. Run it from a lightweight page.

## Verification the script performs

A `200` on the create call is not proof. The script:

1. Reads the view back with `$expand=ViewFields` and prints **what SharePoint actually stored**,
   in order.
2. Diffs stored-vs-requested and prints `missing` / `extra` / `order differs` explicitly.
3. Verifies each field exists via `fields/getbyinternalnameortitle` before creating the view —
   a nonexistent name in `ViewFields` is accepted silently by some SharePoint versions and then
   renders nothing.
4. Prints the view's URL.

The **UNDO** block at the bottom deletes the view by title. It creates a *new* view and never
touches an existing one, so undo is a clean delete — unlike the N2 column script, where undo
would have destroyed data had the sync flows already run.

## Provenance

| Source | File |
|---|---|
| Column order (authority) | `../FRM10-12/live-workbook-data/FRM10-12_2026-09-04_23h08m.xlsx` → `Orders`!`TableOrders` |
| Which columns are Excel formulas | `../FRM10-12/power-query/TableOrders.pq`, step `#"Removed Formula Columns"` |
| Workbook ← SharePoint field renames | `../FRM10-12/power-query/ColumnMap.pq` |
| Live list schema (87 fields + 3 computed) | `sharepoint-lists/Order Items 2026-09-05 1432.csv`, `ListSchema` record |
| The 48 parent-sync columns | `sharepoint-lists/N2 field definitions 2026-09-05.json`, `docs/n2-column-build-sheet.md` |
| Lookup internal names | hand-resolved 2026-09-07 |
| Existing view house style | `sharepoint-lists/view-definitions 2026-09-04 0110.md` |
| Transfer-flow field mapping (the precedent this doc follows) | `docs/order-items-power-automate-flows.md` |
| Script conventions | `scripts/n2_create_columns.js` |

### One inconsistency found on the way, unrelated to the view

`TableOrders.pq`'s `#"Removed Formula Columns"` step lists **seven** columns to drop —
`Archived`, `Estimated Delivery Date`, `Price CAD`, `Price USD`, `Price`, `Navigation Order`,
`Navigation Model` — but the live table has only the six; there is no `Archived` column in
`B5:CE1024`. `Table.RemoveColumns` without `MissingField.Ignore` throws on a missing column, so
either the tracked `.pq` is ahead of/behind the live workbook, or `TableOrders` currently errors
on refresh. Worth a look, separately from this view.

