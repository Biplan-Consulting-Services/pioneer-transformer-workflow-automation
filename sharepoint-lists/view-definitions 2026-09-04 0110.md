# SharePoint view definitions — captured 2026-09-04 01:10

Read live from `_api/web/lists/getbytitle('<list>')/views?$expand=ViewFields` on
`https://ermcopower.sharepoint.com/sites/PioneerPlanificatio`.

**Why this file exists.** Until now no view definition has ever been exported. They lived only
as prose in `BUILD-NIGHT-STATUS.md`, which is in no git repo. If a view were edited or deleted
there was no way to diff or restore it — and one already was: `Overview`, built 2026-09-01
06:37 and gone by 2026-09-04, unrecoverable because SharePoint does not retain deleted view
definitions.

Field names below are **internal names**, which is what CAML and the REST API take. Several
differ from their display names in ways that matter — see the traps at the bottom.

---

## List: `Order Items` (1052 items)

### `All Items` — DEFAULT
74 columns, no filter, `RowLimit` 30. Field list not captured (it is every non-hidden column).
The 19 BO columns added 2026-09-04 were deliberately **not** added to this view.

### `Production Floor`
The staff landing view. `RowLimit` 100.

```
<GroupBy Collapse="FALSE" GroupLimit="100"><FieldRef Name="Location" /></GroupBy>
<OrderBy><FieldRef Name="ManualEstimatedDeliveryDate" Ascending="TRUE" /></OrderBy>
<Where><Eq><FieldRef Name="ItemStatus" /><Value Type="Text">Active</Value></Eq></Where>
```

`Title, Order_Number_TextField, Location, ItemStatus, CoilWinder, ManualEstimatedDeliveryDate`

### `Planning`
FRM10-12's outline level 1, intersected with what `Order Items` carries. `RowLimit` 100.

```
<OrderBy><FieldRef Name="Planned_x0020_Delivery_x0020_Dat" Ascending="TRUE" /></OrderBy>
<Where><Eq><FieldRef Name="ItemStatus" /><Value Type="Text">Active</Value></Eq></Where>
```

`Title, LinkTitle, Client, Location, Status, CoreStatus, Tank, Frame, ISOStack, ISOCoil,
LeadAssembly, CoilingStatus, CoilingDate, StackingDate, AssemblyDate, DryingDate,
Planned_x0020_Tanking_x0020_Date, TestingDate, FinishingDate, Planned_x0020_Delivery_x0020_Dat,
OriginalTankingDate, TankingDateChangeJustification, ManualEstimatedDeliveryDate, ItemStatus`

### `Angelique réunion du lundi`
**Byte-identical to `Planning`.** Verified programmatically: 24 fields vs 24, same order, zero
in either that is not in the other. The CAML differs only in element order (`Where` before
`OrderBy` rather than after), which is semantically the same query.

So this is a `Save view as` copy that was **never actually customised** — not a variant. Either
the customisation is still to come, or it lives in per-user column widths, which are personal
and not part of the definition. Worth asking Angelique whether she got what she wanted.

Fields: identical to `Planning` above.

### `Angelique bobinage`
Winding-focused. No filter at all, so it shows every item including Delivered and Cancelled.

`Title, Client, Location, Status, CoilingStatus, CoilingDate, Planned_x0020_Tanking_x0020_Date,
CoilWinder, Winder`

### `JF - Test`
```
<Where><Eq><FieldRef Name="SAJob" /><Value Type="Boolean">0</Value></Eq></Where>
<GroupBy><FieldRef Name="Model" Ascending="TRUE" /></GroupBy>
<OrderBy><FieldRef Name="Client" Ascending="TRUE" /></OrderBy>
```

`Title, Qty, SAJob, Client, Model, Planned_x0020_Delivery_x0020_Dat`

A **public** view, despite the name reading like a personal experiment. New views are public by
default in SharePoint; this is the reason the bilingual views guide leads with the
personal-vs-public distinction. Not named in the staff guides, deliberately.

### `BO Tracking` — new 2026-09-04 00:41
```
<Where><IsNotNull><FieldRef Name="BO" /></IsNotNull></Where>
<GroupBy Collapse="FALSE" GroupLimit="100"><FieldRef Name="BO" /></GroupBy>
<OrderBy><FieldRef Name="Planned_x0020_Tanking_x0020_Date" Ascending="TRUE" /></OrderBy>
```

`Title, Order_Number_TextField, BO, Location, Planned_x0020_Tanking_x0020_Date,
BO1PartNumber, BO1Description, BO1POIntern, BO1Date, BO1Fournisseur, BO1OK,
BO2PartNumber, BO2Description, BO2POIntern, BO2Date, BO2Fournisseur, BO2OK,
BO3PartNumber, BO3Description, BO3POIntern, BO3Date, BO3Fournisseur, BO3OK`

Renders 73 rows in two groups: `BO` (10) above `OK` (63). Grouping on `BO` puts outstanding
units first because `BO` sorts before `OK`.

---

## List: `Order` (445 items)

### `Direction - Prix (demo)` — new 2026-09-04 01:00
```
<OrderBy><FieldRef Name="Order_x0020_Date" Ascending="FALSE" /></OrderBy>
```

`Order_x0020_Number1, Client, Order_x0020_Date, Province_x002F_State, Qty, Price,
FX_x0020_Rate, Price_x0020_CAD, Price_x0020_USD, Estimated_x0020_Delivery_x0020_D, OrderStatus`

Built on `Order`, not `Order Items`, because price cannot be retrofitted onto `Order Items`'
existing lookup — projected fields are create-time only.

Sorted on `Order_x0020_Date`, a real DateTime, rather than the calculated
`Estimated_x0020_Delivery_x0020_D`: sorting a calculated column that chains onto other
calculated columns is a known SharePoint failure mode.

`(demo)` is in the name on purpose so nobody treats it as a committed report.

---

## Internal-name traps

Read names from `/fields`. Never retype one.

| Display name | Internal name | Trap |
|---|---|---|
| `Tanking End Date` | `TankingDate` | **"End" is dropped** |
| `Delivery End Date` | `DeliveryDate` | **"End" is dropped** |
| `Planned Delivery Date` | `Planned_x0020_Delivery_x0020_Dat` | **truncated at 32 chars** |
| `Unit ID` | `Title` | renamed built-in |
| `Order Number` (Order list) | `Order_x0020_Number1` | note the trailing `1` |
| `Info+` | `Info_x002b_` | `+` encoded |
| `Protector & Switchgear Item #` | `Protector_x0020__x0026__x0020_Sw` | truncated **and** encoded |

A guessed internal name does not error — it silently reads or writes nothing. That is how a
column can appear blank in a view that looks correctly configured.

## How to re-capture this file

REST works from a site-context browser session. PnP PowerShell is blocked on this tenant
(`AADSTS700016`) but that is a third-party AAD app consent issue, **not** a general API block —
schema reads, schema writes and item writes all work. Four repo docs currently say otherwise.

```
GET  _api/web/lists/getbytitle('Order Items')/views?$select=Title,Hidden,DefaultView,RowLimit,ViewQuery&$expand=ViewFields&$top=100
```
