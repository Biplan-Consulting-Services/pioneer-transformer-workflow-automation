# The Pioneer workbook data graph — every Power Query, all five workbooks

Built 2026-09-06 by pulling the M code out of every workbook with
`scripts/Export-PowerQuery.ps1` and scanning it with `scripts/pq_graph.py`. **98 queries across
five workbooks**, all tracked under `power-query/<workbook>/*.pq`. Nothing here is inferred from
file names or from what people said — it is what the queries do.

| Workbook | Queries | Source read |
|---|---|---|
| FRM10-12 | 23 | `FRM10-12/live-workbook-data/FRM10-12_2026-09-04_23h08m.xlsx` |
| FRM11 | 39 | `Workflow-Automation/workbooks/PRO1.FRM11 …xlsx` |
| FRM13 | 20 | `FRM10-12/linked-workbooks/PRO1.FRM13 - Desplan - Auto.xlsx` |
| Archive active | 12 | `FRM10-12/linked-workbooks/Archive active.xlsx` |
| FRM09 | 4 | `FRM09/workbook/PRO1.FRM09 Winding.xlsx` |

## 🔑 One mechanism explains the whole estate

Every workbook resolves every external source the same way — through a SharePoint list named
**`Index`** on `https://ermcopower.sharepoint.com/sites/PioneerPlanificatio`, with two columns
`Title` and `Path`, and an identical `ImportFromIndex(title, tableName)` helper copied into each
file:

```m
shared ImportFromIndex = (sheet, name) =>
    let Path = Table.SelectRows(Index, each [Title] = sheet){0}[Path],
        Workbook = Excel.Workbook(Web.Contents(Path), null, true),
        Table = Workbook{[Item=name, Kind="Table"]}[Data]
    in ReplaceAllErrors(Table, null);
```

**Not one hardcoded workbook URL exists anywhere in the estate.** Every cross-workbook edge below
is a `Title` lookup in that list. Which means:

- Moving a workbook breaks nothing, as long as its `Index` row is repointed. That is why the
  2026-09-04 move of FRM10-12 to `Revue/Formulaires/` did not take the estate down.
- **`Index` is the single highest-value object in this whole system.** It is also a single point of
  failure with no version history anyone is watching, and a comma in a `Path` value would break the
  `Text.BeforeDelimiter` that strips the hyperlink description.
- The eventual FRM10-12 cutover is **one row edit**, not a rewrite. See the recommendation below.

## The graph

```
        SharePoint lists ── Order · Models · Model Revisions · Models SA
                 │  (SharePoint.Tables, Implementation 2.0)
                 ▼
   BO Manager ─► FRM10-12 ◄─ Temps Standard          Archive active
   (TableBO)      ▲    │      (TableJobTimes)         (TableArchiveFRM10_12,
                  │    │                               TableArchiveFRM11,
        LeedTime  │    │ TableOrders                   TableArchiveFRM13)
                  │    ├──────────────► FRM09           ▲   ▲   ▲
                  │    │                                │   │   │
                  │    ├──────────────► FRM11 ──────────┘   │   │
                  │    │      (+ TableCuveCodes,            │   │
                  │    │         TablePeintureCodes,        │   │
                  │    │         TablePioneerCodes)         │   │
                  │    │                    │              /   /
                  │    └──────────────► FRM13 ◄───────────'   /
                  │                       │  TableFournTank  /
                  └───────────────────────┘─────────────────'
                        FRM13-Auto.LeedTime

   Rapport Falcon ─► FRM11   (+ 7 more supplier reports, resolved at runtime)
```

### Reader → source, by `Index` title

| `Index` title | Read by | Tables |
|---|---|---|
| **FRM10-12** | **FRM09** | `TableOrders` |
| | **FRM11** | `TableOrders`, `TableCuveCodes`, `TablePeintureCodes`, `TablePioneerCodes` |
| | **FRM13** | `TableOrders` |
| **FRM11** | FRM13 | `TableFournTank` |
| **FRM13-Auto** | **FRM10-12** | `LeedTime` |
| **Archive active** | FRM10-12 | `TableArchiveFRM10_12` |
| | FRM11 | `TableArchiveFRM10_12`, `TableArchiveFRM11` |
| | FRM13 | `TableArchiveFRM10_12`, `TableArchiveFRM13` |
| **BO Manager** | FRM10-12 | `TableBO` |
| **Temps Standard** | FRM10-12 | `TableJobTimes` |
| **Rapport Falcon** | FRM11 | `TableStatutsCuve`, `SelectedLanguage` |
| *(7 more supplier reports)* | FRM11 | `TableReport` — title computed from `TableSuppliers` at runtime |

## 🔴 There is a cycle, and it involves three workbooks

**FRM10-12 → FRM13 → FRM10-12.** FRM13's `TableOrders` reads FRM10-12's `TableOrders`; FRM10-12's
`ClientLeadTimes` reads FRM13's `LeedTime`, published back through the `Index` as `FRM13-Auto`.

And a longer one: **FRM10-12 → FRM11 → FRM13 → FRM10-12**, since FRM13 pulls `TableFournTank`
from FRM11 to get each order's tank supplier.

Power Query does not deadlock on this — the cycle runs through *different tables*, and each hop
reads a saved `.xlsx` rather than a live evaluation. But the consequence is real:

> **There is no refresh order that produces a consistent estate.** Whichever workbook you refresh
> first is reading at least one other workbook's *previous* state. `LeedTime` in particular is a
> hand-maintained sheet table in FRM13 that FRM10-12 consumes — so a lead-time edit does not reach
> FRM10-12 until FRM13 is saved *and* FRM10-12 is refreshed.

That is very likely the mechanism behind the already-measured **`Order.Lead Time` disagreeing with
FRM13's `LeedTime` on 306 of 342 rows**. It is not overrides; it is a stale hop in a cycle.

## FRM10-12 already reads SharePoint — and that changes the cutover plan

This was not recorded anywhere. FRM10-12 has four queries that hit the SharePoint lists **directly**,
not through Excel:

```m
// Orders.pq
Source  = SharePoint.Tables("https://ermcopower.sharepoint.com/sites/PioneerPlanificatio",
                            [Implementation = "2.0"]),
Orders  = Source{[Title="Order"]}[Items],
result  = FlattenSharePointLookupLists(Orders, SharepointListMetaColumns)
```

Same shape for `Models`, `Model Revisions` and `Models SA`. Two supporting queries do the hard part:

- **`FlattenSharePointLookupLists`** — expands SharePoint lookup columns into plain values. This is
  the problem the `_TextField` mirror columns exist to solve on the SharePoint side, already solved
  on the Excel side.
- **`ApplyColumnMap` + `ColumnMap`** — a declarative rename/retype table keyed by entity name, so
  SharePoint internal names never appear inline in a query.

`TableOrders` then merges those SharePoint reads into its own sheet table on `Order Number` + `Qty`
(order fields) and `PO Item #` (model fields).

**So the machinery for "read the SharePoint lists from Excel" is built, tested and in production
today.** A future `TableOrders` sourced from SharePoint is not new engineering — it is one more
entity in `ColumnMap`.

### ⚠️ And this is exactly why `Refresh All` destroys the workbook

`TableOrders` opens with:

```m
Source = Excel.CurrentWorkbook(){[Name="TableOrders"]}[Content],
#"Removed Formula Columns" = Table.RemoveColumns(Source,
    {"Estimated Delivery Date", "Price CAD", "Price USD", "Price",
     "Navigation Order", "Navigation Model"}),
```

The query **reads the sheet table it writes back to**, and explicitly strips six native formula
columns first. A generic refresh re-lands the table without them. The existing rule ("never
`Refresh All` or COM `RefreshAll` on FRM10-12 — use the Office Script button") now has its
mechanism written down, not just its symptom.

## Per-workbook notes

### FRM09 — 4 queries, one edge

`FRM10-12` → `ImportFromIndex("FRM10-12", "TableOrders")`, plus the three boilerplate helpers.
That is the workbook's *entire* external surface. Whatever is broken in FRM09's references to
FRM10-12's shifted columns, **it is not Power Query** — this query takes the whole table with no
column list. Look at the sheet formulas instead.

### FRM13 — 20 queries, the busiest consumer

`TableOrders` reads FRM10-12's `TableOrders` and aggregates **per order** (it splits `21535-1/2` at
the first `-`, groups, takes `List.Min` of `Tanking Date` and `List.First` of `PO Item #`). Eleven
columns are selected: `Order`, `Client`, `KVA and KV`, `Type`, `Order Date`, `Qty`, `PO Item #`,
`Duplicate`, `Engineering Required`, `Initial Promised Date`, `Tanking Date`.

`TableFournisseursCuve` reads FRM11's `TableFournTank` and splits the unit ID the same way — so
FRM13 gets tank supplier **per order**, taking whichever unit's supplier survives the dedup.

`LeedTime` is a plain `Excel.CurrentWorkbook` sheet table — 18 rows, columns `CLIENT`, `DÉLAI`,
`PIÈCE CRITIQUE 1`, `FOURNISSEUR`, `PIÈCE CRITIQUE 2`, `FOURNISSEUR2`, `Lead time`, `Notes`. It is
**hand-maintained in FRM13 and consumed by FRM10-12**, which matches what the user described.
`ManualDataUpdate` is a parallel 39-column table — FRM13's override mechanism, the same idea as
FRM11's `OverrideJoin`.

⚠️ **Worth one check, not asserted:** `TableOrders`'s two `Table.ExpandTableColumn` steps both
expand `Client Desired Date` out of `#"Select Columns"`, but that step's column list does not
include it. Read statically, that should raise *"The column 'Client Desired Date' of the table
wasn't found"* on every refresh. The sheet table does have the column with data — which could mean
the query is fine and I am misreading the step chain, or that the last successful refresh predates
the change and the sheet has been stale since. **Refresh FRM13 once and watch for the error**
rather than acting on this.

### Archive active — 12 queries, the archive tier

Holds `Archive FRM10-12`, `Archive FRM11`, `Archive FRM13` and `Archive BO` — one archive per live
workbook. Its `TrackRemoteTable` / `Query1` call `ImportFromIndex` with a **runtime-computed title**
from a `RemoteFileIndex`, so it is generic over whatever it is pointed at. `EnforceFormats`,
`AddMultipleNullColumns` and `TrackRemoteTable` are shared with FRM13 — copied, not referenced.

### The copy-paste helper problem

`ImportFromIndex`, `ReplaceAllErrors`, `Index`, `SortBySortKeys`, `AddAddedTimestamps`,
`TrackRemoteTable`, `EnforceFormats` and `AddMultipleNullColumns` are **duplicated across
workbooks**, not shared. FRM13 carries `Index`, `ReplaceAllErrors` **and** `Index (2)`,
`ReplaceAllErrors (2)`, `ImportFromIndex (2)` — two copies of the same helper in one file.

They have already drifted: `ReplaceAllErrors` is 257 chars in FRM11, 282 in FRM09 and 285 in
FRM10-12/FRM13; `ImportFromIndex` is 288 in FRM11, 315 elsewhere, 329 for FRM13's second copy.
**Nobody can fix a helper once.** Now that `Export-PowerQuery.ps1` and `Sync-PowerQuery.ps1`
round-trip, a shared `power-query/_shared/*.pq` set pushed into every workbook is cheap — but it is
a change to live workbooks, so it needs the user's go-ahead, not a quiet fix.

## What this means for the Order Items migration

1. **`TableOrders` has four consumers, not one.** FRM09, FRM11 and FRM13 all read it, plus
   FRM10-12's own SharePoint merge. Reshaping or retiring it is a four-way break.
2. **The cutover is genuinely cheap when it comes.** Publish a SharePoint-sourced workbook exposing
   a table named `TableOrders`, repoint one `Index` row, and FRM09, FRM11 and FRM13 follow with no
   M changes. FRM10-12's own `ColumnMap` / `FlattenSharePointLookupLists` queries are the template
   for building it.
3. **The lead-time cycle should be cut, not preserved.** `Clients.Lead Time` on SharePoint already
   exists (roadmap item on the `Clients` sync). Once `LeedTime` lives on the `Clients` list, the
   FRM10-12 ⇄ FRM13 cycle disappears and the 306-row disagreement stops being possible.
4. **Add `Index` to whatever gets backed up.** Everything above depends on one list nobody is
   watching.

## Reproducing

```powershell
./Export-PowerQuery.ps1 -WorkbookPath <workbook> -OutputPath ..\power-query\<name> -SafeCopy
```

`-SafeCopy` reads a temp copy so the original is never opened — use it on any workbook whose
"refresh data when opening" setting is unknown, FRM10-12 above all. Then:

```
python scripts/pq_graph.py
```
