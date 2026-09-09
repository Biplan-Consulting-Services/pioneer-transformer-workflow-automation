# Pre-cutover audit — 2026-09-09 evening

Run against the snapshots taken at 17:55–17:58, after X4 / X2 / X1 / N8 had all applied.

| source | |
|---|---|
| `workbooks/FRM10-12 2026-09-09 1755.xlsx` | 1,001 units · 82 columns |
| `sharepoint-lists/Order Items 2026-09-09 1758.csv` | 1,124 rows · 143 columns |
| `sharepoint-lists/Order 2026-09-09 1757.csv` | 449 rows |
| `Models` / `Model Revisions` 1758 | 390 / 391 |
| `workbooks/Archive active 2026-09-09 1755.xlsx` | 5,196 archive rows |

**Question asked:** is any column or value missed, or badly interpreted, for the final
transfer?

**Answer: no missed column, one real gap that is already a known decision, and one open
question about date storage.** Details below, worst first.

---

## 1 · The one thing I would fix before Thursday

### `Order - Order Folder` — 106 source values reaching nothing

`Order.Order Folder` is populated on **106 of 449** orders. `Order Items.Order - Order
Folder` is populated on **0 of 1,124**.

This is roadmap 38 and it is a deliberate omission, not an oversight: a SharePoint
hyperlink is an object on both read and write, the shape was never sourced, and a wrong one
either fails every row or writes nothing. It is excluded from `v007` and from the N3
`Order` flow.

What is new is the **cost, measured**: 106 orders carry a folder link that will not exist
in `Order Items` after cutover. Whether that matters depends on whether anyone follows
those links, which I cannot tell from here.

🔑 **The window closes Thursday.** While the transfer flow exists it could carry them once
the shape is known; after it is deleted, N3 is the only route and it also excludes the
column. Either source the shape from one real trigger payload before the run, or accept
losing the links and record that.

---

## 2 · Column coverage — nothing else is missed

### Workbook → the flow

Of the **82** columns in `TableOrders`, the flow reads **47**. The other 35 break down
cleanly:

| | count | verdict |
|---|---|---|
| native Excel formula columns | 6 | correctly excluded — they are formulas, not data |
| parent data the workbook itself pulls *from* SharePoint | 29 | must not be pushed back |

Every one of the 29 was checked individually for a home on the destination:

- **25 land in the 48 parent-sync columns** — `Phases` → `Mod. Rev. - Phases`,
  `PO` → `Order - PO`, `Overcoil` → `Mod. Rev. - Overcoil`, and so on.
- **`KVA and KV`** → `Mod. Rev. - kVA`. The display name is misleading; the Model Revisions
  column is internally `kVA_x0020_and_x0020_kV` and does hold the combined value.
- **`Price Value`** → `Order - Price`.
- **`Lead Time`** and **`Ing. Due Date`** are *not* on `Order Items`, and should not be.
  `Lead Time` reaches the workbook through the `ClientLeadTimes` merge from FRM13, not from
  the unit row; `Ing. Due Date` lives on `Order`. Both remain reachable to the viewer.

**So: no workbook column is silently dropped.**

### The flow → Order Items

`CreateOrderItem` writes 122 fields, `UpdateOrderItem` 130 — the 8-field difference is the
create branch not writing values that only exist on an update. Of the 130: **81 own-unit
fields and 49 parent-sync** (20 `Ord` / 5 `Mdl` / 24 `Rev`).

---

## 3 · 🟢 The viewer reproduces FRM10-12's shape exactly

This was the biggest open risk and it comes out clean.

```
workbook TableOrders                    82 columns
TableOrdersColumnOrder emits            76 columns
in the workbook but not emitted          6  <- exactly the native formula columns
emitted but not in the workbook          0
same order where both present          True
```

The six the viewer does not emit are `Price`, `Estimated Delivery Date`, `Price CAD`,
`Price USD`, `Navigation Order`, `Navigation Model` — Excel formulas that live in the sheet
and are re-applied by Excel, exactly as they are in the current workbook.

**All 76 data columns, in the identical order.** FRM09 / FRM11 / FRM13 / BO Manager see no
shape change.

⚠️ One thing this does *not* prove: that the viewer workbook's sheet still carries those six
formula columns as native formulas. Confirm at the 1.2 refresh.

---

## 4 · Rows

```
workbook units                1,001
Order Items units             1,124
in both                         998
workbook only                     3   20877R1-1/1 · P20002-1/1 · P21911_A-1/1
Order Items only                126
workbook units whose Order is missing from the Order list:  0
```

- The **3 workbook-only** units all have an `Order` row, so `CheckOrderMatch` passes and the
  run **creates** them. Re-diff after the run should be **0**.
  🔑 `P21911_A-1/1` is new since this morning — it was not in the set X4 addressed, and it
  needs no action because its order already exists.
- The **126 list-only** rows are the archived orphans (104 previously known) plus the
  **21 units archived out of the workbook today**, all confirmed against `Archive active`
  at `Location = LI` with a real Delivery Date, 3–9 September. Normal completion.

### The workbook lost 21 units and gained 3 since this morning

Validated one by one against `TableArchiveFRM10_12`: **21 of 21** are `LI` with a delivery
date. The 3 gained are `22158-1/3 … 3/3`, a new order from the Power App fan-out.

---

## 5 · Value shape

### Marker columns — 52 disagreements, all in one direction

Yesterday's join found 1,013/1,013 agreement. Today: **52 disagreements**, all four
R-columns (`Tank` 23, `ISO Stack` 6, `ISO Coil` 14, `Lead Assembly` 9). The five `x`
columns and `SFRA` remain perfect.

**Every one is the same way round: the workbook has a marker, the list does not. Zero the
other way.** That is staff production progress since the last run, waiting for the sync — it
is precisely what the final run exists to push across, and it is evidence the conversion
logic is right rather than evidence against it.

### The rest, unchanged from yesterday's analysis

`Frame` is a three-value Choice typed `logical`; `Witness/Other` is free text;
`Engineering Required` and `LDs` lost their third state at the destination; `SA Job` is
genuinely boolean; `CSA` is empty on both sides.

---

## 6 · The 48 parent-sync columns

All **48 present**. Eight are populated on 0 rows — and seven of those are **empty at
source**, so there is nothing to carry:

| column | source | source rows populated |
|---|---|---|
| `Mod. Rev. - Duplicate Order` | Model Revisions | **0 / 391** |
| `Mod. Rev. - Primary Voltage` | Model Revisions | **0 / 391** |
| `Mod. Rev. - Secondary Voltage` | Model Revisions | **0 / 391** |
| `Mod. Rev. - Spec_Date` | Model Revisions | **0 / 391** |
| `Mod. Rev. - Spec_Revision` | Model Revisions | **0 / 391** |
| `Order - Sales Notes` | Order | **0 / 449** |
| `Order - New model to be created` | Order | not in the export — Choice, needs a REST check |
| `Order - Order Folder` | Order | **106 / 449** ← §1 |

`Primary Voltage` / `Secondary Voltage` are also 0-populated in the workbook, so the whole
chain is empty and consistent.

---

## 7 · ⚠️ Date storage — the open question

Two conventions are in use on `Order Items`. Eastern midnight (`04:00`/`05:00Z`) is the one
the estate expects; a large set of values sit at **UTC midnight** (`00:00:00Z`) instead.

| column | values | off-convention |
|---|---|---|
| `Tanking End Date` | 139 | **139 — all of them** |
| `Coiling End Date` | 239 | 93 |
| `Stacking End Date` | 191 | 93 |
| `Assembly End Date` | 190 | 93 |
| `Drying End Date` | 175 | 93 |
| `Testing End Date` | 120 | 78 |
| `Finishing End Date` | 90 | 58 |
| `Planned Delivery Date` | 360 | 58 |
| `Planned Tanking Date` | 1,032 | 60 |
| `Original Tanking Date` | 1,058 | 55 |
| `Delivery End Date` | 102 | 36 |
| `Manual Estimated Delivery Date` | 155 | 24 |
| **clean** | | `Order - Order Date`, `Order - Initial Promised Date`, `BO1/2/3 Date`, and **every `Status Date` N8 wrote** |

The repeated **93** across four stage columns says one batch wrote them, not staff.

**Why it may not matter:** if these are Date-Only columns, SharePoint ignores the time and
this is cosmetic. **Why it might:** if any is DateTime-with-time, `2026-07-16T00:00:00Z`
displays to an Eastern viewer as **15 July, 8pm** — a date off by one, on production
records.

🔑 **One check settles it**, and it is cheap: read the `Format` of `Tanking End Date` from
`_api/v2.0/sites/root/lists/<id>/columns`. If `DateOnly`, close this. If not, it needs a
pass — and note the final run will *rewrite* most of these from Excel, so doing it after the
run is the right order.

Encouraging sign: N8 wrote 246 `Status Date` values today and **all** landed at
`04:00/05:00Z`. Whatever produced the `00:00Z` values is not a current writer.

---

## 8 · What I could not verify

- **The run itself.** There is no dry run for the transfer flow. This audit covers the
  inputs and the mapping, not the execution.
- **That the viewer's M actually executes.** Structure, names and logic check out; Power
  Query has never run it. That is what gate 1.2 is for.
- **`Order - New model to be created`** — the source column is absent from the CSV export
  (Choice columns can be), so I could not confirm whether it is empty at source or a
  mapping gap. One REST read.
- **Whether the stripped `DataMashup` identity costs anything.** Unproven in both
  directions.

---

## 9 · Decisions for you

1. **`Order Folder`** — source the hyperlink shape before the run, or accept losing 106
   links. The window closes when the flow is deleted.
2. **Date storage** — run the one `Format` check; if it is not `DateOnly`, schedule a
   normalisation pass *after* the run.
3. **Excel Online** — second browser save today, by a second person. The library setting
   (*Open in the client application*) is the only fix that does not depend on everyone
   remembering. The narrowed rule is in `../FRM10-12/CLAUDE.md`: ordinary cell edits have
   not been shown to hurt it; **reordering columns of a query-backed table has**.

---

## 10 · Verdict

Nothing is missed and nothing is badly interpreted. The mapping is complete, the viewer
reproduces the workbook's shape column-for-column and in order, every parent column is
either populated or empty at source, and the only marker disagreements are the workbook
being ahead of the list — which is what the run fixes.

The two things carrying real risk into Thursday are **the untested viewer M** (gate 1.2) and
**`Order Folder`**, which is a decision rather than a defect.
