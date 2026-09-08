# Source-vs-list comparison — 2026-09-08

**Question asked:** is all the data actually there? Compared `Order Items` against **both** upstream
sources, field by field, on the mapping taken **out of the live v006 flow definition** rather than
from any doc — so the column pairing is what the flow really does, not what anyone believed.

| | |
|---|---|
| list | `sharepoint-lists/Order Items 2026-09-08 0557.csv` — 1,117 rows |
| FRM10-12 | `workbooks/FRM10-12 2026-09-08 0219.xlsx` · `TableOrders` `Orders!B5:CE1024` — 82 cols, **1,019 units** |
| BO Manager | `workbooks/BO Manager 2026-09-08 0615.xlsx` · `TableBO` `Sheet1!B5:X1024` — 23 cols, **1,019 rows** |
| comparable units | **1,013** (the 6 absent are exactly the named survivors) |
| fields compared | **49** from `TableOrders` + **19** from `TableBO` = 68 |

BO Manager provenance: `cp:lastModifiedBy` **Jean-Francois Fortin**, `dcterms:modified`
**2026-09-04T18:53:12Z** — so its content is the Sep 4 state the run read.

## Verdict: nothing is missing

🟢 **`MISSING = 0` on all 68 fields.** There is no column, in either source, where the upstream
holds a value and the list does not.

🟢 **BO Manager → list is exact: 0 missing, 0 differing on all 19 fields.**

## The apparent differences were all artefacts — checked, not assumed

A first pass flagged 13 `TableOrders` fields as "differing". Every one resolved:

| what looked wrong | what it actually is |
|---|---|
| 386 cells across 10 flag columns (`ISO Coil`, `ISO Stack`, `Lead Assembly`, `DB`, `Impulse`, `Oil Analysis`, `Partial D`, `SFRA`, `Temperature Rise`, `CSA`) | The workbook marks these with **`x`, `r` or `y`**, and the flow converts presence to a Boolean. Verified directly: **list boolean == (workbook cell non-blank), 0 mismatches on all ten.** My normaliser simply didn't know the marker convention. |
| `OrdEngineeringRequired` 605, `OrdLDs` 161 | `Y`/`N` → Boolean. Correct. |
| `Configuration` 9 rows | The workbook genuinely holds `datetime.time(0,0)` in those cells; the list holds `'0'`. **Faithful transfer of bad source data** — a workbook cleanup item, not a migration fault. |
| `Technical Notes` 6 rows | The workbook cell contains **HTML** (`<div class="externalclass…`); the list holds the same text with HTML entities. Representation, not loss. |

The 10 `Coiling Date` rows carrying the `ec` marker were excluded by design — the guard turns them
into null, and `CoilingStatus` correctly reads `In Progress`. All six `{Stage}Status` expressions
share one identical rule and all six carry the `toLower` guard, so **P3 is confirmed live in v006**.

## Finding: `BO` = 84 is resolved, and the docs' "76" was wrong

| | |
|---|---|
| list rows with a `BO` value | **84** |
| …of which units also in `TableOrders` | **66** — and all 66 match `TableBO` exactly |
| …of which orphan rows | **18** — pre-existing values the run cannot reach |
| `TableBO` rows with a `BO` value | **69** (not 76), of which 66 map to a live unit |

**66 transferred + 18 surviving on orphans = 84. There is no join fan-out** — the worry flagged
earlier is closed. ⚠️ But **the long-standing "76" figure is wrong**: `TableBO` holds **69**. Every
doc quoting 76 (including `R1`'s card and the handover) should be corrected.

## 🔴 Finding: 844 stale `Pending` stage statuses, and *why the run could not clear them*

Rows where the workbook stage date is **blank** but the list still carries a status:

| stage | stale | value |
|---|---|---|
| Testing | **813** | `Pending` |
| Stacking | 26 | `Pending` |
| Finishing | 4 | `Pending` |
| Drying | 1 | `Pending` |
| Coiling / Assembly | 0 | — |
| **total** | **844** | |

The flow writes `null` for these (blank date → `null`), and the run rewrote all 1,013 rows. They
survived anyway.

**Mechanism — worth stating plainly because it changes how remediation must be built:
SharePoint's `Update item` does NOT clear a field passed `null`; it leaves the existing value.**
This is the same behaviour the docs already rely on to keep the blank `{Stage}StartDate` marker
alive through a run — so it is consistent, not a surprise, but its other edge is that **no amount
of re-running will ever remove a stale value.**

These 844 are `R10`'s predicted damage, **already done**: the trigger flow's stage-stamping wrote
`Pending` into stages the backfill deliberately left blank, before that flow was disabled.

🟢 **The remediation key is undamaged.** `X1`/`R14` keys on a **blank `{Stage} Start Date`**, and all
**eight** start-date columns are **0 populated**. So the marker survived the run intact; the 844
`Pending` values are misleading on screen but do not break the cleanup.

⚠️ **Consequence for `X1`:** it must **write an explicit value** to clear these — passing `null`
will silently do nothing. That is a design constraint, not a preference.

## Bearing on R7

`R7` removes the BO mapping so future runs stop overwriting SharePoint-native BO edits. The
null-does-not-clear behaviour makes that *more* important, not less: while the mapping is in place
every run reasserts the Excel value, and once removed the list value simply persists — which is the
desired end state.

## Method notes

- The mapping was extracted from `UpdateOrderItem`'s 130 `item/*` parameters in the v006 definition
  and classified by source: **49** `TableOrders`, **25** `Model Revisions`, **19** `TableBO`,
  **14** other expressions, **13**+1 `Order`, **4** `Models`, **3** composes.
- **9 fields are derived, not copied** — the six `{Stage}Status`, `OrdClientDateStatus`,
  `OrdEngineeringRequired`, `OrdLDs` — plus `Tank`, which is `not(equals(…,''))`. Comparing them as
  copies would have produced 1,000+ false mismatches.
- Internal→display names came from `_api/v2.0/…/lists/{id}/columns`; 18 of 68 do not round-trip by
  decoding alone (`CoilingDate` → **"Coiling End Date"**, `OrdLDs` → **"Order - LDs"**,
  `BO1PartNumber` → **"BO1 Part Numbre"**, and `Planned_x0020_Delivery_x0020_Dat` is truncated).
- Normalisation had to handle, all of them traps this repo has hit before: Excel serial dates,
  `[{"@odata.type":…,"Value":"X"}]` wrappers, French vs English decimal separators, Boolean `False`
  reading as non-empty, and the `EC`/`TBD` marker guards.
