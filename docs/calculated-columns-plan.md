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
`Price Value`, a date cascade → `YEAR(...)` → cross-list lookup into
`Table_USD_CAD_Conversion_Rate[Year]/[Rate]` (approximate match, next-smaller-year
fallback).

**Correction, verified 2026-08-31**: this doc previously described the date cascade as
`Delivery Date` → `Tanking Date` → `Estimated Delivery Date` → `Initial Promised Date`.
The live formula's cascade is only two deep — `Estimated Delivery Date`, falling back to
`Initial Promised Date`, and falling back to the *string* `"Invalid date for conversion"`
if both are blank (which makes `YEAR()` error, so blank-on-both rows currently show an
error, not a price). `Delivery Date` and `Tanking Date` are not referenced.

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
bilingual hyperlink label).

**Correction, verified against the live workbook 2026-08-31** (`FRM10-12_2026-08-31_09h41m.xlsx`,
`xl/tables/table1.xml`): this doc previously said `Navigation Model` "branches between the
`Models` and `Models SA` list URLs depending on whether `Order` contains `SA`". It does not,
and there is no evidence it ever did in this revision. The live formula is a single
unconditional `HYPERLINK` into the **`Models Revisions`** list (`viewid=5526fc48-6a40-4e8b-a015-7cb3f2c32705`),
keyed on `PO Item #` — no `SA` branch, no `Models`/`Models SA` URLs at all. The
"Models-vs-Models-SA branch is moot after the fusion" argument below was therefore arguing
against something that isn't there; the recommendation to drop still stands, but on the
Hyperlink-output ground alone, not that one.

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

---

# Build pass — 2026-08-31 (supersedes the "zero of the 7" conclusion above)

Verified live against SharePoint and against `FRM10-12_2026-08-31_09h41m.xlsx`
(`xl/tables/table1.xml`). **Decisions taken by the user this session**: drop the three
hyperlink columns entirely (`Price`, `Navigation Order`, `Navigation Model`); drop
`Archived`; inline the small reference tables rather than creating SharePoint lists for
them; build the estimation.

## Correction to this doc's headline conclusion

"Zero of the 7 become plain SharePoint calculated columns" was too strong. It treated
`TableCanadianProvince` (13 static rows) and `Table_USD_CAD_Conversion_Rate` (6 rows,
extended once a year) as cross-list lookups. They are small and static enough to **inline
into the formula text**, which removes the cross-list wall entirely for `Price CAD`/
`Price USD`. Those two are real, plain calculated columns — no flow needed.

The live `Order` list also already disproves the "`ClientLeadTimes` needs a SharePoint home
first" prerequisite: `Lead Time` exists there as a plain `Number`, and the list's one
pre-existing calculated column `Ing. Due Date`
(`=[Initial Promised Date]-(7*([Lead Time]+4))`) already consumes it.

## Where each column has to live, and why

Calculated columns cannot read across lists, so placement is forced by where the *inputs*
already are — not by preference.

| Column | List | Why |
|---|---|---|
| `Price CAD` / `Price USD` | **`Order`** | Inputs `Price [Currency]` and `Province/State [Text]` are `Order` fields. Price is also per-order, not per-unit — pushing it onto 1038 `Order Items` rows from 441 orders duplicates one price across units and invites double-counting in reports. |
| Estimated Delivery Date (full, milestone-aware) | **`Order Items`** — but **not** as a calculated column | The milestone dates (`Coiling/Tanking/Testing/Finishing End Date`, `Tank Delivery Date`, `Manual Estimated Delivery Date`) are per-unit on `Order Items`, but the formula also needs `Order Date` + `Lead Time` (on `Order`), `TODAY()` (banned in calculated columns), and `BO` (**exists on neither list**). Spans both lists in both directions → Power Automate flow, on a daily recurrence so the `MAX(TODAY(), …)` branches don't freeze at last-save. |
| Estimated Delivery Date (order-level projection) | **`Order`** | FRM10-12's *final fallback branch only* (`Order Date + 90 + Lead Time*7`). Both inputs are live on `Order`; no `TODAY()`, no cross-list. This is the only branch expressible at order level. |

## Live data coverage (checked 2026-08-31, all 441 `Order` items)

- `Price` non-null 426/441, non-zero 411
- `Province/State` non-null 411/441 — Canadian: `QC` 233, `AB` 40, `ON` 30, `PE` 2 (=305);
  remainder US (`USA` 45, `WI` 14, `US` 13, `GA` 6, `PA` 5, `KY`/`AL`/`CO` 4 each, `MN`/`TX` 3,
  `TN` 2, `FL`/`LA`/`NO` 1)
- `Order Date` 439/441, `Lead Time` 441/441

`NO` (1 row) is not a US state or Canadian code — treated as non-Canadian (USD). Worth a
data check.

## Column specs — exact text

Create in this order; each references the one before it.

### 1. `Estimated Delivery Date (Projected)` — Calculated → Date and Time, Date Only
**BUILT 2026-08-31, live on `Order`.** Not added to any view.
```
=IF(ISBLANK([Order Date]),"",[Order Date]+90+(IF(ISBLANK([Lead Time]),52,[Lead Time])*7))
```
The `52` mirrors FRM10-12's `XLOOKUP(..., 52)` default for a client missing from
`ClientLeadTimes`. Verified: Order Date `2025-11-19`, Lead Time `26` → `2026-08-18`
(= +90 +182 days). Internal name `Estimated_x0020_Delivery_x0020_D`.

### 2. `FX Rate` — Calculated → Number, 4 decimals — NOT YET BUILT
```
=IF(YEAR([Estimated Delivery Date (Projected)])>=2029,1.47,IF(YEAR([Estimated Delivery Date (Projected)])>=2028,1.43,IF(YEAR([Estimated Delivery Date (Projected)])>=2027,1.39,IF(YEAR([Estimated Delivery Date (Projected)])>=2026,1.38,IF(YEAR([Estimated Delivery Date (Projected)])>=2025,1.44,1.35)))))
```
Inlines `Table_USD_CAD_Conversion_Rate` (`AI1:AJ7` on sheet4): 2024→1.35, 2025→1.44,
2026→1.38, 2027→1.39, 2028→1.43, 2029→1.47. Descending `>=` reproduces XLOOKUP match
mode `-1` (exact, else next smaller year).

**Deliberate difference from Excel:** for a year before 2024 the workbook returns `#N/A`
(`Price CAD`) / `"Year not found in conversion table"` (`Price USD`); this floors to 1.35
instead. Extend this formula each year as the workbook table is extended.

### 3. `Price CAD` — Calculated → Currency, 2 decimals, LCID 4105 — NOT YET BUILT
```
=IF(OR([Province/State]="AB",[Province/State]="BC",[Province/State]="MB",[Province/State]="NB",[Province/State]="NL",[Province/State]="NT",[Province/State]="NS",[Province/State]="NU",[Province/State]="ON",[Province/State]="PE",[Province/State]="QC",[Province/State]="SK",[Province/State]="YT"),[Price],[Price]*[FX Rate])
```

### 4. `Price USD` — Calculated → Currency, 2 decimals, LCID 1033 — NOT YET BUILT
```
=IF(OR([Province/State]="AB",[Province/State]="BC",[Province/State]="MB",[Province/State]="NB",[Province/State]="NL",[Province/State]="NT",[Province/State]="NS",[Province/State]="NU",[Province/State]="ON",[Province/State]="PE",[Province/State]="QC",[Province/State]="SK",[Province/State]="YT"),[Price]/[FX Rate],[Price])
```

Both inline `TableCanadianProvince` (`AL1:AM14` on sheet4). Direction check against the
workbook: a province code *not* found → the order is priced in USD → `Price CAD = Price *
Rate`, `Price USD = Price`. Found → priced in CAD → `Price CAD = Price`,
`Price USD = Price / Rate`.

**Note on the year source:** per the user's instruction this session, the
`Initial Promised Date` fallback in the workbook's date cascade is dropped — the rate year
comes from the projected delivery date alone. For orders already in production the
projected date can land in a different year than the true (milestone-aware) estimate, which
would pick a different rate. Revisit once the `Order Items` flow exists.

## Still open

- The three columns above are specced but **not built** — the create call was blocked by a
  local tool-permission classifier, not by SharePoint.
- The milestone-aware Estimated Delivery Date flow on `Order Items` (needs a `BO` field
  created first — it exists on neither list today).
