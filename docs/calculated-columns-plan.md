# Calculated columns — SharePoint port analysis

`infrastructure-overview.md` flagged 7 native Excel-formula columns on `TableOrders` for a
parallel-run-then-cutover: `Price`, `Estimated Delivery Date`, `Price CAD`, `Price USD`,
`Archived`, `Navigation Order`, `Navigation Model`. The plan was "SharePoint calculated
column where possible, Power Automate flow where SharePoint's formula language can't
express it." This doc is that actual analysis — the exact formula text for all 7, pulled
directly from the workbook XML (`xl/tables/table1.xml`'s `calculatedColumnFormula`
elements), not guessed, plus what each one depends on and where it should actually go.

## The two hard walls

SharePoint calculated columns hit two hard limits, and every one of the 7 columns below
runs into at least one of them:

1. **No cross-list lookups.** A calculated column can only reference fields on the *same*
   list item — never another list's/table's data. Any formula doing an `XLOOKUP`/`VLOOKUP`
   against a separate table can't become a calculated column, full stop.
2. **No volatile functions, no Hyperlink output.** `TODAY()`/`NOW()` are blocked in
   calculated columns (SharePoint won't recompute them without a resave). Calculated
   columns also can't produce a `Hyperlink`-typed result — only Text/Number/
   Currency/Date/Yes-No.

**Result: none of the 7 columns can be a plain SharePoint calculated column.**

## Per-column findings

### Price (`Q` in `TableOrders`)
```
IF(TRUE, HYPERLINK(orderListUrl & TEXTBEFORE([Order], "-"), [Price Value]))
```
The `IF(TRUE,...)` wrapper is dead code (always true) — this formula's only real job is a
hyperlink whose *display value* is `[Price Value]`. Hyperlink output isn't available to
calculated columns.

**Recommendation: drop.** `Price Value` already holds the real number as a plain field. The
hyperlink was pure Excel-UI convenience (click the price, jump to the Order list) — a
SharePoint list view doesn't need that trick; its own Lookup-column UI already provides
one-click navigation to related items.

### Estimated Delivery Date (`BX`)
Depends on: `Delivery Date`, `Manual Estimated Delivery Date`, `Finishing Date`,
`Testing Date`, `Tanking Date`, `Coiling Date:Drying Date` (range), `Tank Delivery Date`,
`Order Date`, `BO`, `Order`, plus a cross-list lookup into `ClientLeadTimes[Client]` →
`[Lead Time]`, plus `TODAY()`.

Logic: use the real `Delivery Date` if known; else a manual override; else walk backward
through production milestones (Finishing → Testing → Tanking → Coiling/Drying), adding a
fixed lead buffer (7/10/14/21 days) from `TODAY()` or the milestone date, plus a 30-day
penalty unless `BO` is `"OK"`/blank; if no milestone exists yet, project `Order Date` + 90
days + a per-`Client` lead time (from `ClientLeadTimes`, defaulting to 52 weeks if the
client isn't found).

Blocked by: the `ClientLeadTimes` cross-list lookup **and** `TODAY()` — two separate
disqualifiers.

**Recommendation: Power Automate flow.** Needs `ClientLeadTimes` as a real SharePoint list
first (see Prerequisites below) — it's currently only a native Excel table.

### Price CAD (`CC`) / Price USD (`CD`)
Depends on: `Province/State` → cross-list lookup into `TableCanadianProvince[Code]`,
`Price Value`, a date cascade (`Delivery Date` → `Tanking Date` → `Estimated Delivery Date`
→ `Initial Promised Date`, first non-blank) → `YEAR(...)` → cross-list lookup into
`Table_USD_CAD_Conversion_Rate[Year]/[Rate]` (approximate match, next-smaller-year
fallback).

Logic: if the order's province is a recognized Canadian code, `Price Value` is already CAD
(Price CAD = as-is) / needs conversion (Price USD = ÷ rate). Otherwise the reverse (Price
CAD = × rate, Price USD = as-is).

Blocked by: two separate cross-list lookups.

**Recommendation: one Power Automate flow, both fields** (same year/rate lookup, just
branch which side gets multiplied). Needs `TableCanadianProvince` and
`Table_USD_CAD_Conversion_Rate` as SharePoint lists first.

### Navigation Order (`CE`) / Navigation Model (`CF`)
Depends on: `Order`, `PO Item #` (Navigation Model only), and the defined name
`SelectedLanguage` (a single cell, `Orders!$E$2`, holding `"FR"`/other — used to pick a
bilingual hyperlink label). Navigation Model also branches between the `Models` and
`Models SA` list URLs depending on whether `Order` contains `"SA"`.

Blocked by: Hyperlink output again, plus `SelectedLanguage` has no per-item SharePoint
equivalent (it's a single global Excel cell, not list data).

**Recommendation: drop, both.** Same reasoning as `Price` — `Order Items`/`Order` already
have real Lookup columns to `Order`/`Models`/`Model Revisions` (built in workstream 1, step
8), and SharePoint's own Lookup UI already provides one-click navigation. The Models-vs-
Models-SA branch in `Navigation Model` is also moot now that the Models SA fusion
(workstream 4) means there's no separate `Models SA` list to branch to. This confirms the
doubt `infrastructure-overview.md` already raised ("may not need to exist at all") —
dropping is the right call, not just a possibility.

### Archived (`CB`)
**Has no formula at all right now.** Checked directly in the workbook: zero `<f>` elements
across all 1000 data rows, and `Archived` doesn't appear in `xl/calcChain.xml` except for an
unrelated header-translation helper. Every non-blank cell (359 of ~1000 rows) holds the
static cached text `"Exists"`, the rest are blank — there's no live logic behind these
values today, just whatever was last computed before the formula was lost (likely a past
refresh/paste-as-values accident, consistent with this workbook's documented fragility
around generic refreshes).

Spot-checking rows marked `"Exists"` shows ordinary *active* orders (`Location` values like
`TA`/`XT`/`FO`/`BO`), not delivered/cancelled ones — so whatever this column used to flag,
it isn't today's archive/purge criteria (`Location = LI` + `Delivery Date`, or
`Location = AN`, which is what `TableOrders.pq`'s actual archive-row-removal logic uses).
**Correction**: `infrastructure-overview.md` currently lists `Archived` alongside the other
6 as if it's still a live formula column — that's now known to be wrong (see the correction
made there as part of this doc's write-up).

**Recommendation: don't port — this needs a decision, not a formula translation.** Likely
just dead weight, superseded by `Order Items`' real `Item Status` field (which already
captures the actual delivered/cancelled/regrouped state this column may once have
approximated). Flagging to you directly rather than guessing further, since the original
formula can't be recovered from static values alone: **confirm it's safe to drop before
anyone builds against it.**

## Prerequisite for the two Power Automate flows

`ClientLeadTimes`, `TableCanadianProvince`, and `Table_USD_CAD_Conversion_Rate` are all
**native Excel tables today, not SharePoint lists** — Power Automate's SharePoint connector
can't read them where they sit now. Before either flow (Estimated Delivery Date; Price
CAD/USD) can be built for real, these three need a SharePoint home, or to be hardcoded into
the flow instead:
- **`Table_USD_CAD_Conversion_Rate`** (`Year`/`Rate`, 6 rows, manually extended yearly) —
  small and simple enough that hardcoding into the flow is a reasonable option, but a tiny
  SharePoint list keeps it editable without a flow redeploy, consistent with how every other
  reference table in this migration works.
- **`TableCanadianProvince`** (province name/code list) — same, small and static, either
  option is fine.
- **`ClientLeadTimes`** — has several other columns beyond `Client`/`Lead Time`
  (`PIÈCE CRITIQUE 1/2`, `FOURNISSEUR`/`FOURNISSEUR2`, `Notes`), suggesting it's edited more
  like real operational data than a static reference table. **Recommend a real SharePoint
  list for this one**, not hardcoding.

## Summary — destination per column

| Column | Destination |
|---|---|
| Price | Drop |
| Estimated Delivery Date | Power Automate flow (needs `ClientLeadTimes` as a SharePoint list first) |
| Price CAD | Power Automate flow (shared with Price USD) |
| Price USD | Power Automate flow (shared with Price CAD) |
| Archived | **Needs a decision — flagged above, not a port** |
| Navigation Order | Drop |
| Navigation Model | Drop |

Zero of the 7 become plain SharePoint calculated columns — the original "calculated column
where possible" framing doesn't apply to any of them in practice.
