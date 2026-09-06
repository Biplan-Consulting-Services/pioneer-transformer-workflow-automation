# FRM11 → FRM10-12 coupling — roadmap item 26, answered

Read 2026-09-06 from `workbooks/PRO1.FRM11 - Planification Approbation Cuve.xlsx`
(2,285,110 bytes, saved 2026-09-06 00:28). Everything below comes from the workbook's own
Power Query M (extracted from the `DataMashup` part) and its loaded sheet data — not from
inference.

## The short answer

**FRM11 reads FRM10-12 directly, on every refresh, and its whole row set is derived from
`TableOrders`.** It is not a loose sync — `TableOrders` is FRM11's *root* query. Eight
supplier report sheets hang off it, and each of those drives an exchange with an outside
company.

```
SharePoint list "Index"  (Title → Path)
        │
        ├── "FRM10-12"        → TableOrders          ─┐
        │                       TableCuveCodes        │
        │                       TablePeintureCodes    │  the FRM10-12 dependency
        │                       TablePioneerCodes    ─┘
        │
        ├── "Archive active"  → TableArchiveFRM11
        │                       TableArchiveFRM10_12
        │
        └── "Rapport <supplier> (new)" × 8  → TableReport   (the supplier workbooks)

TableOrders
   → Imported FRM10_12 Data   (10 columns kept, renamed to FRM11's French vocabulary)
       → FournTank            (filter, dedup, join archive, purge, self-ref overrides)
           → the "fourn Tank" sheet, TableFournTank, 890 live rows
           → SupplierReport(x) × 8 → the 8 "Rapport …" sheets
```

## 🔑 The Index list — the single most useful thing in this workbook

Every external workbook is resolved through a SharePoint list, not a hardcoded URL:

```m
shared Index = let
    Source = SharePoint.Tables("https://ermcopower.sharepoint.com/sites/PioneerPlanificatio"),
    Index = Source{[Name="Index"]}[Content],
    #"Removed Other Columns" = Table.SelectColumns(Index,{"Title", "Path"}),
    ...

shared ImportFromIndex = (sheet, name) =>
    let Path = Table.SelectRows(Index, each [Title] = sheet){0}[Path],
        Workbook = Excel.Workbook(Web.Contents(Path), null, true),
        Table = Workbook{[Item=name, Kind="Table"]}[Data]
    in ReplaceAllErrors(Table, null);
```

Consequences worth knowing:

- **The 2026-09-04 move of FRM10-12 to `Revue/Formulaires/` did not break FRM11** — provided the
  `Index` row titled `FRM10-12` was repointed. One list row is the whole migration surface for
  every workbook built this way. ⚠️ **Not verified against the live list** — it needs one look.
- It is also the **kill switch**: repointing that one row swings every consumer at once. If a
  SharePoint-backed replacement for `TableOrders` is ever published as a workbook, FRM11 moves
  over with a single cell edit and no M changes.
- `Path` is stored as a SharePoint hyperlink and the query strips the `, description` tail
  (`Text.BeforeDelimiter(_, ",", RelativePosition.FromEnd)`), so a comma in a filename would
  break it.

## Exactly what FRM11 takes from `TableOrders`

Ten columns, and no more (`Imported FRM10_12 Data`):

| `TableOrders` column | renamed to | note |
|---|---|---|
| `Order` | `NUMÉRO DE CUVE` | the join key |
| `Client` | `CLIENT` | |
| `Type` | `Type` | |
| `KVA and KV` | *(consumed)* | folded into the composite below, then dropped |
| `PO Item #` | `DUP ou # Client` | |
| `Location` | `location` | |
| `Tanking Date` | `Date encuvage` | |
| `Original Tanking Date` | `Original Tanking Date` | |
| `Tanking date change justification` | same | |
| `Tank` | *(consumed)* | looked up → `Status`, then dropped |

Plus a computed `CLIENT, TYPE TRANSFO, SIZE` = `Client - Type KVA and KV`.

`TableLocales` in the workbook flags these same columns `Imported From Pioneer = TRUE`, so the
dependency is declared in data as well as in code — a good place to check before changing
anything.

⚠️ **Hyperlinks are stripped** on `NUMÉRO DE CUVE`, `CLIENT`, `Type`, `KVA and KV`
(`Remove Hyperlinks`). FRM10-12 stores those as hyperlink cells; a plain-text SharePoint
replacement would feed the function values it does not expect. Harmless, but it is a shape
assumption.

## 🔴 `Tank` is a status code in Excel and a Yes/No in SharePoint

This is the one concrete defect the analysis turned up.

In `TableOrders`, `Tank` holds a **two-letter tank status code** — FRM11 joins it against a
combined `TableCuveCodes` + `TablePeintureCodes` + `TablePioneerCodes` lookup to produce a
readable `Status`. Live values in the 2026-09-04 workbook snapshot: `R` on 74 rows, blank on 945.
`R` is `Reçu Pioneer`.

The transfer flow maps it as:

```
item/Tank   →   @not(equals(item()?['Tank'], ''))
```

**The code is discarded and only "is it non-empty" survives.** `Order Items.Tank` is a Yes/No
column, `True` on 143 of 1,052 in the 2026-09-05 export. So:

- The tank status vocabulary does not reach SharePoint at all.
- Today that costs nothing *semantically*, because `R` is the only code in live use — so
  `Tank = true` currently happens to mean "Reçu Pioneer". It stops being true the moment anyone
  types a different code in FRM10-12.
- ⚠️ **Correcting an earlier note in this repo:** `Order Items.Tank` was recorded as `True` on
  1,052 of 1,052. It is not — it is 143. The rest of that note (that `Tank` is not the FRM11
  join key) still holds: the join key is `Order` / `Unit ID`.

## Row set — FRM11 is *narrower* than `Order Items`, by design

`FournTank` filters `TableOrders` before anything else:

```m
Table.SelectRows(Source, each [NUMÉRO DE CUVE] <> null
    and not Text.Contains([NUMÉRO DE CUVE], "SA")
    and not Text.Contains([NUMÉRO DE CUVE], "W")
    and not Text.Contains([NUMÉRO DE CUVE], "R")
    and not Text.Contains([NUMÉRO DE CUVE], "OS"))
```

then de-duplicates on the key, then anti-joins `Rows to purge`. Measured against the
2026-09-05 `Order Items` export:

| | rows |
|---|---|
| FRM11 live (`TableFournTank`) | **890** |
| `Order Items` | 1,052 |
| matching on `Unit ID` | **821** |
| on `Order Items`, absent from FRM11 | 231 |
| … excluded by the SA/W/R/OS filter | 75 |
| … explained by the "Already Tanked" purge | **115** |
| … remaining | **41** |
| in FRM11, absent from `Order Items` | **69** |

Two things fall out of that, and both are useful:

- **The 69 decompose exactly into the known missing-row diff.** 65 of them are orders
  `22143`–`22155`, created *after* the Sep 1 transfer run; the other 4 are `P1_001-1/1`,
  `P20002-1/1`, `P20004-1/2`, `P20004-2/2` — four of the seven known test rows. FRM11 already
  has all of them. That is independent proof its FRM10-12 read is live and current, and a second
  confirmation of the "65 new orders + ~7 test rows" split.
- **The purge rule reproduces cleanly with zero false positives.** No row present in FRM11
  satisfies it. Of the 41 left over, **11 are the already-known real orphans** — the 8 units of
  order `22021` and the 3 `E`-prefixed ones (`E21010-1/2`, `E21010-2/2`, `E21014-1/1`).

### The purge rule reads FRM10-12's `Location` and `Status` vocabularies

```m
"Already Tanked" = List.Contains({"XT","TE","FI","LI"}, [Location.1])
                   or ([Location.1] = "TA" and Text.Contains([Status.1], "TE"))
```

Against the **archive** copy of FRM10-12, in **two-letter codes**. The transfer flow converts
those same codes to display names on the way into SharePoint (`LI` → `Livraison`, and so on).
So a SharePoint-native replacement would have to translate back, or the purge silently stops
firing and FRM11 grows without bound.

Note the code collision this walks straight into: `TE` means **Test** in `Location` and
**Terminé** in `Status`, and the rule uses both meanings in one line.

## What FRM11 owns, and does *not* get from FRM10-12

`TableLocales` is the authority — 58 columns, each flagged. The live `fourn Tank` sheet holds 26
of them. Everything not flagged `Imported From Pioneer` is either FRM11's own (`Fournisseur CUVE`,
`Fournisseur Peinture`, `CUVE P.O.`, `P.O. Peinture`, `Commentaire Pioneer`, the RAD / B-WALL
dates), calculated in-sheet, or imported from a supplier report.

Manual entries survive refreshes through two mechanisms worth knowing about:

- **`OverrideJoin`** — a generic left-join where a non-null override value beats the imported one,
  column by column, types restored afterwards.
- **`ShadowTableColumn`** — copies a column into a shadow column and stamps an update date, only
  re-copying after `refreshRateDays`. That is how "original" values (`Original Tanking Date`,
  `Original Required Tank Delivery Date`, `Original Required Paint Date`) are frozen.

## ✅ Roadmap item 27 answered too — the vocabularies never drifted

The open question was which tank-status vocabulary is current, FRM10-12's `List` sheet or FRM11's
live values. **The question was malformed: they are two different vocabularies, both current.**

FRM11 does not keep its own copy of the code tables — it *imports* them from FRM10-12:

```m
shared TableCuveCodes     = ImportFromIndex("FRM10-12", "TableCuveCodes");
shared TablePeintureCodes = ImportFromIndex("FRM10-12", "TablePeintureCodes");
shared TablePioneerCodes  = ImportFromIndex("FRM10-12", "TablePioneerCodes");
```

and lands them on its `Validation` sheet. They are identical to FRM10-12's by construction. The
loaded values confirm the three-table reading recorded in `infrastructure-overview.md`
(8 · 8 · 2), with one addition: `TablePeintureCodes` carries a **ninth row with a blank `Statut`
and the code `-`**, and `Verbose Tank Codes Ref` is `Table.Distinct` on `Code`, so a future
collision between the three tables would silently drop a row.

The values that looked like drift — `Dessin reçu`, `BC reçu`, `Terminée`, `Problème` — are
**`Tank Supplier Status` / `Paint Supplier Status`, which are computed from the supplier reports**,
a different axis with a different vocabulary. `TableLocales` marks both `Calculated = TRUE`.
Live distribution on the 890 rows:

| column | values |
|---|---|
| `Status` *(from FRM10-12's `Tank` code)* | `Reçu Pioneer` 15 · blank 875 |
| `Tank Supplier Status` *(from supplier reports)* | blank 514 · En production 134 · Livrée 108 · Problème 70 · Terminée 27 · Dessin reçu 20 · BC reçu 14 · B-Wall 3 |
| `Paint Supplier Status` *(from supplier reports)* | blank 779 · Reçue 61 · Livrée 40 · Terminée 10 |

So: **nothing to reconcile, and nobody to ask.** The `List` sheet is the master for the
FRM10-12-side code vocabulary; the supplier-status vocabularies are FRM11's own and belong to
the supplier exchange.

⚠️ The one thing that *is* worth noting: **`Status` is populated on 15 rows out of 890.** The
`Statut Cuve` / `Statut Peinture` vocabularies are, in practice, essentially unused — only
`R` ever appears. Anyone planning to migrate them should know they are carrying an empty column.

## What this means for the Order Items migration

**FRM11 is a hard dependency on `TableOrders` keeping its shape.** Specifically it needs:

1. The **column names** `Order`, `Client`, `Type`, `KVA and KV`, `PO Item #`, `Location`,
   `Tanking Date`, `Original Tanking Date`, `Tanking date change justification`, `Tank` — all ten
   are referenced by literal string in `Table.SelectColumns` / `Table.RenameColumns`. A rename
   breaks the refresh with an error, not a silent blank.
2. `Location` and `Status` in **two-letter codes**, for the purge rule.
3. `Tank` as a **code**, for the `Status` lookup.
4. The three code tables to keep their names and their `Statut` / `Code` columns.
5. The `Index` row titled `FRM10-12` to keep resolving.

Behind that sit **890 live rows, 8 supplier report sheets and 8 outside companies**. FRM11 is not
a downstream report that can lag a week — it is how tanks get ordered.

### Recommendation

**Do not remove or reshape `TableOrders` as part of this migration.** Nothing in the current plan
requires it: the transfer flow *reads* FRM10-12 and writes SharePoint, so both consumers can
coexist indefinitely. The failure mode to guard against is a later cleanup pass that decides the
workbook is now redundant.

When FRM10-12 *is* eventually retired, the migration path is unusually cheap and should be
recorded now while it is understood:

- Publish a SharePoint-sourced workbook exposing a table named `TableOrders` with those ten
  columns, in codes.
- Repoint the `Index` row titled `FRM10-12` at it.
- FRM11 needs **no M changes at all.**

The alternative — pointing FRM11's queries at the SharePoint lists directly — means rewriting
`Imported FRM10_12 Data`, translating `Location` and `Status` back to codes, and reinstating the
`Tank` code that the transfer flow currently discards. Strictly more work for no benefit.

## Still worth one check

- **The `Index` list row for `FRM10-12`** — confirm its `Path` points at
  `.../General/FAB/Revue/Formulaires/FRM10-12.xlsx`. If it still holds the pre-move path, FRM11
  has been refreshing against a dead link (or a stale cached copy) since 2026-09-04. Everything
  above says it is *probably* fine — FRM11 has orders `22143`–`22155`, which only exist post-move
  — but the row itself was not read.
- **Whether `Tank`'s code should reach SharePoint.** One flow-expression change would carry it as
  text. Worth doing only if anyone actually intends to use the `Statut Cuve` vocabulary, which
  today they do not.

## Reproducing this

**The M code is tracked** — `power-query/FRM11/*.pq`, 39 files, one per query, exported
2026-09-06. Read those rather than re-opening the workbook.

They were produced by **`scripts/Export-PowerQuery.ps1`**, written for this analysis as the
missing counterpart to `FRM10-12/scripts/Sync-PowerQuery.ps1`. Same Excel COM surface
(`$wb.Queries` → `.Name` / `.Formula`), opposite direction, so the two round-trip: export, edit
the `.pq`, push back with `Sync-PowerQuery.ps1 -Apply`.

```powershell
./Export-PowerQuery.ps1 -WorkbookPath "..\workbooks\PRO1.FRM11 - …xlsx" -ListOnly
./Export-PowerQuery.ps1 -WorkbookPath "..\workbooks\PRO1.FRM11 - …xlsx" -OutputPath ..\power-query\FRM11
```

⚠️ It opens `ReadOnly`, never saves, and **never refreshes** — that constraint is deliberate and
must not be relaxed, because a generic refresh on FRM10-12 wipes its native formula columns.

`scripts/frm11_join.py` reproduces the row-set table above against a
`sharepoint-lists/Order Items …csv` export.
