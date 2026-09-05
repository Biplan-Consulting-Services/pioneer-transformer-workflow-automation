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

### 2. `FX Rate` — Calculated → Number, 4 decimals
**BUILT 2026-08-31, live on `Order`.** Internal name `FX_x0020_Rate`.
```
=IF(ISBLANK([Order Date]),"",IF(YEAR(D)>=2029,1.47,IF(YEAR(D)>=2028,1.43,IF(YEAR(D)>=2027,1.39,IF(YEAR(D)>=2026,1.38,IF(YEAR(D)>=2025,1.44,1.35))))))
```
where `D` is `([Order Date]+90+(IF(ISBLANK([Lead Time]),52,[Lead Time])*7))`, written out
in full at each of the five occurrences.

Inlines `Table_USD_CAD_Conversion_Rate` (`AI1:AJ7` on sheet4): 2024→1.35, 2025→1.44,
2026→1.38, 2027→1.39, 2028→1.43, 2029→1.47. Descending `>=` reproduces XLOOKUP match
mode `-1` (exact, else next smaller year).

**Why it recomputes the projected date inline instead of referencing column 1.** The first
build did reference `[Estimated Delivery Date (Projected)]`. That produced `error;#1` on
the 2 orders with a blank `Order Date`: column 1 returns `""` for those, and a *second*
calculated column reading that `""` through `YEAR()` errors — `ISBLANK()` on a chained
calculated column does **not** catch it. Rebasing on `[Order Date]`, a real base field,
fixes it. **Rule for this list: guard on a base field, never on another calculated column.**

**Deliberate difference from Excel:** for a year before 2024 the workbook returns `#N/A`
(`Price CAD`) / `"Year not found in conversion table"` (`Price USD`); this floors to 1.35.
Extend this formula each year as the workbook table is extended.

### 3. `Price CAD` — Calculated → Currency, 2 decimals, LCID 4105
**BUILT 2026-08-31.** Internal name `Price_x0020_CAD`.
```
=IF(ISBLANK([Order Date]),"",IF(OR([Province/State]="AB",[Province/State]="BC",[Province/State]="MB",[Province/State]="NB",[Province/State]="NL",[Province/State]="NT",[Province/State]="NS",[Province/State]="NU",[Province/State]="ON",[Province/State]="PE",[Province/State]="QC",[Province/State]="SK",[Province/State]="YT"),[Price],[Price]*[FX Rate]))
```

### 4. `Price USD` — Calculated → Currency, 2 decimals, LCID 1033
**BUILT 2026-08-31.** Internal name `Price_x0020_USD`.
```
=IF(ISBLANK([Order Date]),"",IF(OR([Province/State]="AB",[Province/State]="BC",[Province/State]="MB",[Province/State]="NB",[Province/State]="NL",[Province/State]="NT",[Province/State]="NS",[Province/State]="NU",[Province/State]="ON",[Province/State]="PE",[Province/State]="QC",[Province/State]="SK",[Province/State]="YT"),[Price]/[FX Rate],[Price]))
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

## Verification (2026-08-31, all 441 `Order` items)

Recomputed every row independently against `Price`, `Province/State` and `FX Rate` and
compared to what SharePoint stored:

- **410 rows checked, 0 mismatches, 0 `#ERROR` rows.**
- Rate spread is real, not degenerate: 1.35 ×15, 1.44 ×25, 1.38 ×285, 1.39 ×114, blank ×2.
- The 2 blank rows are the orders with no `Order Date` (ids 86, 541) — blank by design now,
  not errors. Id 86 has a real `Price` (101,027.37) but no date, so no rate can be known;
  id 541 has no `Price` either. **Worth fixing the source data.**
- Direction confirmed against the workbook: province *not* in the Canadian list → order is
  priced USD → `Price CAD = Price × Rate`, `Price USD = Price`. In the list → priced CAD →
  `Price CAD = Price`, `Price USD = Price ÷ Rate`.

None of the four columns were added to any view — nothing changed for the site's 54 members
until someone adds them deliberately.

## Still open

- The milestone-aware Estimated Delivery Date flow on `Order Items` (needs a `BO` field
  created first — it exists on neither list today). Until it exists, `FX Rate` picks the
  rate year from the order-level projection, which for an order already in production can
  land in a different year than the true estimate and so pick a neighbouring rate.
- `Province/State` holds `NO` on 1 row — neither a US state nor a Canadian code. Currently
  treated as non-Canadian (USD). Data check worth doing.
- 30 of 441 orders have no `Province/State`; they fall to the non-Canadian branch and are
  reported as USD-priced. Confirm that default is right.

## How much does `TODAY()` actually matter? (measured 2026-08-31, all 1038 `Order Items`)

`TODAY()` appears in four of the seven Estimated Delivery Date branches, always as
`MAX(TODAY(), <milestone>) + <buffer>` (Finishing 7, Testing 10, Tanking 14,
Coiling..Drying + Tank Delivery 21). It is a **floor, not a scheduler**: its only job is to
stop the formula reporting a delivery estimate that is already in the past for a unit still
in production.

Live population:

| Situation | Rows | Branch | `TODAY()` relevant? |
|---|---:|---|---|
| Delivered (`Delivery End Date` set) | 385 | real date | No |
| `Manual Estimated Delivery Date` set | 171 | override | No |
| No milestone reached yet | 61 | `Order Date + 90 + Lead Time*7` | No |
| Milestone in the **future** | 400 | `MAX` returns the milestone | No |
| **Milestone in the past** | **21** | `MAX` returns TODAY | **Yes** |

Of the 21: `TankingDate` 14, `TestingDate` 5, `Coiling..Drying` 2. Staleness median 5 days,
max 75, only 6 over 30 days. Worst case — tanking 75 days ago, undelivered — without
`TODAY()` the estimate lands 61 days in the past; with it, today + 14.

**Consequences for the unbuilt flow:**
1. It does **not** need to rewrite all 1038 items daily. It only needs rows where the latest
   milestone is in the past and `Delivery End Date` is empty — ~21 rows/day. Trivial flow.
2. A plain calculated column would be correct for ~98% of rows and wrong only for stuck
   units, and wrong *visibly* (a past-dated delivery estimate), not silently. That is a
   legitimate cheaper option if a flow isn't wanted — decide deliberately, don't default.
3. Caveat on the 400 future-dated rows: a calculated column only recomputes on item save,
   so they stay right while people keep editing them and go stale exactly when a unit
   stalls — the same rows as (1).

**Field-name mapping confirmed** (`Order Items` internal names match FRM10-12's
`TableOrders` column names one-for-one): `CoilingDate`, `DryingDate`, `TankingDate`,
`TestingDate`, `FinishingDate`, `DeliveryDate`, `TankDeliveryDate`,
`ManualEstimatedDeliveryDate`. The earlier worry that the `* End Date` display names might
not line up was unfounded.

## Start Dates — present in schema, empty in practice (checked 2026-08-31)

`Order Items` carries 8 stage Start Date columns (`CoilingStartDate`, `StackingStartDate`,
`AssemblyStartDate`, `DryingStartDate`, `TankingStartDate`, `TestingStartDate`,
`FinishingStartDate`, `DeliveryStartDate`). **All 8 are populated on 0 of 1038 rows** —
verified by full scan and independently by an `ne null` filter. The matching End Date
columns do hold data (Tanking 975, Delivery 385, Coiling 209, Stacking 166, Assembly 158,
Drying 146, Testing 95, Finishing 71).

FRM10-12 has no equivalent: `TableOrders` has 82 columns and none contain "Start". These are
a SharePoint-side addition with no data behind them.

**So they cannot contribute to the estimate today.** If they ever get populated they would
add something the Excel formula structurally cannot do — distinguish *started but not
finished* from *not started*, where today the formula only ever walks backward through
completion dates. Treat that as a future improvement contingent on the data existing, not
as part of the initial port.

**Naming smell worth a look:** `Tanking End Date` is set on 975/1038 rows, 400 of them
dated in the *future*. It is being used as a planned/target date, not a completion stamp.
Harmless for the formula (`MAX` picks whichever is later) but the display name misleads.

## Where the Estimated Delivery Date computation should live

**Decision direction (user, 2026-08-31): fold it into the existing `Order Items - created or
updated trigger` flow** rather than building a standalone flow. Consistent with this repo's
2026-08-13 naming decision — that flow is named after its trigger precisely so additional
concerns get added to it instead of spawning flows that re-trigger each other.

**This is necessary but not sufficient.** A create/update trigger fires only when the item
changes. The whole purpose of `TODAY()` is to keep the estimate honest for items that are
*not* changing — a unit stalled in production. Those are exactly the ~21 rows measured
above, and a create-or-update trigger will never fire for them. Needed:

1. **In the create/update flow** — recompute whenever milestone data actually changes.
   Immediate, no lag.
2. **A separate daily recurrence** — re-stamp only rows where the latest milestone is in the
   past and `Delivery End Date` is empty (~21 rows/day). Small and cheap; do not rewrite all
   1038.

**Two documented lessons from this repo apply directly** (see "Hard-won build lessons",
2026-08-14, in `order-items-power-automate-flows.md`):
- **Self-trigger loop** — writing the estimate back onto the item re-fires the trigger.
  Guard with "skip the update if the computed value already equals the stored value", the
  same pattern Flow A uses for TextFields.
- **Date null handling** — use `empty()`, not `= ""`; a SharePoint Date field's trigger value
  is `null`, and writing `""` back to a Date field breaks it. The estimate has genuine blank
  cases (no `Order Date`), so this will be hit.

**Open blocker: `BO`.** A real `TableOrders` column, present on neither SharePoint list, so
the `+30 unless BO is "OK"/blank` penalty cannot be computed. Either migrate `BO` onto
`Order Items` or ship the estimate without the penalty — needs a decision. The flow also
needs `Order Date` and `Lead Time` from the parent order via a `Get item` on the
`Order Number` lookup.

## `BO` — corrected 2026-08-31 (an earlier version of this section was wrong)

**Retraction.** This doc briefly claimed `BO` held dollar amounts and that the `+30` applied
to 926 of 980 rows (94.5%). **That was wrong**, caused by a cell-parsing bug: empty cells in
the sheet XML are self-closing (`<c r="BZ6" s="1"/>`), and the extraction regex used
`<c r="BZ(\d+)"([^>]*)>(.*?)</c>`, which on a self-closing cell ran past it and captured the
*next* column's value. `BO` (`BZ`) was therefore being read as `Price Value` (`CA`). Any
parser for these sheets must handle both `<c .../>` and `<c ...>...</c>`.

**Actual `BO` values** (column `BZ`, rows 6–985, 980 data rows, correctly parsed):

| `BO` value | Rows | Meaning (confirmed by user) | Effect |
|---|---:|---|---|
| blank | 918 | no back-ordered parts needed | exempt |
| `"OK"` | 54 | transformer has everything it needs to be produced | exempt |
| `"BO"` | 8 | back-ordered parts outstanding | **+30 days** |

There are **no numeric values and no `0`** in this column in the live workbook. The user
recalled a `FALSE`/`0` state meaning "no back-order parts"; in this copy that state is
represented by blank, which the formula already exempts.

**So the `+30` applies to 8 of 980 rows (0.8%)** — a genuine exception, exactly as the
formula's shape implies. `IF(OR([BO]="OK",[BO]=""),0,30)` is **faithful and correct as
written**; the "`BO = 0` is a bug" concern raised earlier does not exist and needs no
decision.

**Do not confuse with `Location = "BO"`.** Column `AI` (`Location`) separately uses `BO` as a
location code on 45 rows. Two unrelated meanings of the same two letters in the same table.

### Consequence for the build

`BO` drops to low priority. Shipping the estimate without it is wrong by 30 days on at most
8 rows, and only on those that have also reached a production milestone (the `+30` appears
only in the four milestone branches). Options, unchanged in mechanism but no longer urgent:

1. **Reuse the Step 3 upsert (recommended when convenient).** `BO` is already a column on
   `TableOrders`, which that flow already reads. One `BO` column on `Order Items` (**Single
   line of text** — it holds `"OK"`/`"BO"`, not numbers) plus one field mapping.
2. **Read `BO Manager` live.** Excel Online (Business) → `TableBO` at
   `/sites/PioneerPlanificatio/Shared Documents/General/FAB/Achat/BOs/BO Manager.xlsx`
   (confirmed live 2026-08-31, 177 KB). No list migration.
3. **Ship without it.** Wrong on ≤8 rows. Reasonable given the measured impact.

## Start Dates — confirmed purpose (user, 2026-08-31)

The empty Start Date columns are **intentional forward scaffolding**, not an oversight: they
are there to receive data from **Monday.com** and to support a future split between
*progress tracking* and *planning*. Planned counterparts (`Planned Tanking Date`,
`Planned Delivery Date`) are to be added so the two concerns stop sharing columns.

This corroborates the naming smell recorded above — `Tanking End Date` carries 975/1038
values with 400 dated in the future, i.e. it is already doing double duty as a planned date.
Splitting planned from actual resolves an existing conflation rather than only enabling a
future feature.

## Flow sequencing — confirmed (user, 2026-08-31)

Compute the estimate in the create/update flow now; fold it into a general daily-update flow
later. The measurements support this ordering: create/update-only is correct for 1017 of
1038 rows, and the ~21 stalled rows are the only ones needing the daily pass. Shipping
create/update first loses very little.

## Shipped state — `Order` list, end of 2026-08-31

All four columns live and in the **All Items** default view (`FX Rate` deliberately left out
of the view as an internal helper; it still exists on the list). `Price CAD`/`Price USD`
positioned immediately after `Price`; `Estimated Delivery Date (Projected)` after
`Ing. Due Date`.

Final formulas for the two price columns add an `ISBLANK([Price])` guard — without it an
order with no price rendered as `$0.00`, which reads as "this costs nothing" rather than
"unknown":
```
=IF(OR(ISBLANK([Order Date]),ISBLANK([Price])),"",IF(<canadian province test>,[Price],[Price]*[FX Rate]))
=IF(OR(ISBLANK([Order Date]),ISBLANK([Price])),"",IF(<canadian province test>,[Price]/[FX Rate],[Price]))
```

Final verification: 441 items, **410 verified against an independent recomputation, 0
mismatches, 0 error rows, 16 correctly blank**, and no null-price order renders a value.
Spot checks: `WRG3025` price 6,000.00 → CAD 8,280.00 / USD 6,000.00; `WRG3023` price
4,492.80 → CAD 6,200.06 / USD 4,492.80 (both non-Canadian, ×1.38).

## How to actually sync `BO` — two mechanisms

**The key point: you do not sync against `BO Manager` yourself in option 1.** FRM10-12's
Power Query already does it — `BackOrders.pq` (`ImportFromIndex("BO Manager","TableBO")`) is
merged onto `TableOrders` as the `BO` column, joined on `Order`. By the time any flow reads
`TableOrders`, `BO` is already present.

### Option 1 — ride the existing Step 3 upsert (least work)
1. Create `BO` on `Order Items` — **Single line of text** (holds `"OK"`/`"BO"`, never a number).
2. Add one field mapping in the Step 3 Excel→SharePoint flow: `TableOrders[BO]` → `Order Items[BO]`.
3. Re-run the upsert.

Cost: one column, one mapping line. **Downside: it bakes in a dependency on FRM10-12** —
values are only as fresh as the last Power Query refresh *and* the last upsert run. That is
the workbook this migration exists to retire. (Also note this repo's standing rule: never a
generic Refresh All on FRM10-12.)

### Option 2 — read `BO Manager` directly from Power Automate (recommended)
1. Create the same `BO` text column on `Order Items`.
2. Excel Online (Business) → **List rows present in a table**:
   - Location: SharePoint Site `PioneerPlanificatio`
   - Library: `Documents`
   - File: `/General/FAB/Achat/BOs/BO Manager.xlsx`
   - Table: `TableBO`
3. Join key: `TableBO[Order]` ↔ `Order Items[Unit ID]` (`Title`) — the same key
   `BackOrders.pq` joins on, and the same unit-ID format `Order Items.Title` already holds.
4. Write `BO` only when the value differs (self-trigger guard, as with every other flow here).

**Recommended** despite being slightly more work: it drops the FRM10-12 dependency entirely,
which is the direction of this whole migration. Option 1 re-creates the coupling being
removed.

Caveats for option 2: turn **pagination on** (the connector defaults to 256 rows); the source
must be a real named Excel Table (`TableBO` is); a desktop-Excel lock on the file can fail the
connector. **`TableBO`'s exact column names are unverified** — confirm them in the file before
building; only the join column (`Order`) and the value column (`BO`) are known from the
Power Query.

**Priority: low either way.** The `+30` affects 8 of 980 rows, and only those that have also
reached a production milestone. Shipping the estimate without `BO` is a defensible interim.

---

# Settled 2026-09-05 — `TODAY()`, the refresh window, and where the lead time really lives

## `TODAY()` is accepted. The freeze is the real problem.

Tested live: a calculated column on `Order Items` using `TODAY()` **is accepted by SharePoint**, so
the long-standing volatile-function restriction does not kill the design. Branches 1, 2 and 7 —
which never call `TODAY()` — work as a pure calculated column.

What remains is that a calculated column recomputes **only when the item is written**. A
`TODAY()`-based value therefore freezes at the last write and drifts one day further out of date
every day after. A correct-looking value today is not evidence: that row was written today.

⚠️ **A second-order trap worth testing before building on it.** `TODAY()` in a SharePoint
calculated column is widely UTC-based rather than site-local. A **01:00 Eastern** refresh happens to
neutralise that — 05:00/06:00Z stamps the correct Eastern date and freezes it for the day. But any
row edited between roughly **20:00 and midnight Eastern** recomputes with UTC already on tomorrow
and reads **a day ahead** until the next pass. That is the same symptom the whole timezone
workstream exists to fix, arriving by a different route. **Check the existing test column on
`Order Items` after 8pm Eastern**: if it shows tomorrow's date, this is real.

## The nightly refresh — 01:00 Eastern, and the two costs to design around

Decided: a nightly pass that touches rows so SharePoint re-evaluates the formula. The flow computes
nothing; writing any field back to the row is enough.

Two costs, neither a reason not to do it:

1. **It re-fires the `Order Items` trigger flow, once per touched row.** Put a **trigger condition**
   on that flow so a touch-only update never creates a run — trigger conditions are evaluated
   *before* the run is created, so they cost nothing, unlike a first-action Condition which still
   consumes a run.
2. **Version bloat.** Touching all 1,052 rows nightly is ~384,000 versions a year on a list whose
   rows already carry 17+. **Cap version history first.**

Filtering to only rows whose value can actually change (`Item Status = Active`, `Delivery End Date`
and `Manual Estimated Delivery Date` both null, milestone already in the past) cuts the work by
roughly 50×. That is an optimisation, not a correctness requirement.

## Branch 7's lead time — FRM13, not `Order.Lead Time`

Branch 7 is `Order Date + 90 + LeadTime × 7`. The lead time comes from **FRM13**
(`PRO1.FRM13 - Desplan - Auto.xlsx`, `Pioneer Planification/General/FAB/Suivi/Dessin`; working copy
at `FRM10-12/linked-workbooks/`), sheet `DelaisApproParClients`, table **`LeedTime`** — 17 clients
plus a **`GENERIC VALUE` row of 26 SEM**, alongside the critical part and supplier driving each.
FRM10-12 queries it in as `ClientLeadTimes`.

🔴 **`Order.Lead Time` is NOT that value and must not feed branch 7.** Of the 342 orders whose
client appears in `LeedTime`, **306 disagree and 36 agree**. And the values layer by *date*, not by
order — HYDRO QUEBEC's 240 orders split `26` (144, 2024-02 → 2026-04), `20` (84, 82 of them 2026)
and `28` (12, **all** 2026-08). Each is a snapshot of what the number was thought to be at order
entry, never backfilled; FRM13's current 28 only appears from this August.

**Design:** put `LeedTime` on the `Clients` list, with `GENERIC VALUE`'s 26 as the **column
default** rather than a fake client row — `Clients` holds 98 names of which only 42 appear on
orders, and a sentinel row would pollute every picker and filter. Sync **`Lead Time`** down to
`Order Items`; leave `Pièce critique` / `Fournisseur` on `Clients` as reference one lookup away.
Because the values are drift rather than overrides, the sync **corrects** 228 of HQ's 240 orders.

Two clients need pairing by hand — `CITY OF RED DEER` ↔ `RED DEER` and `HYDRO OTTAWA` ↔
`OTTAWA HYDRO`; the other 15 match on name. And **eyeball the 82 HQ orders sitting at `20` in 2026
before the first run**: if any was a faster date actually promised to a customer, the sync rewrites
it.

Retire the Excel formula's `XLOOKUP(..., default 52)` at the same time — it contradicts FRM13's own
generic value of 26, so the two paths currently differ by six months on any client missing from the
table.
