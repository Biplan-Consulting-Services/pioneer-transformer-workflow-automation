# Transfer flow forensics — build night 2, 2026-09-04

Track A (`claude-83`). **Untracked — Track D needs to commit this.** Every claim states how it
was verified so it can be re-run rather than trusted.

Corrects `order-items-power-automate-flows.md` and `cutover-runbook-2026-09-01.md`, **both of
which are written as though the Sep 1 transfer run never happened. It did.**

## Read this first

1. **The Sep 1 run happened** — 06:42 EDT, 40m29s, status `Failed`, and it wrote ≥913 rows.
   `Failed` is the known false alarm. Two repo docs say the run never occurred; they are wrong.
2. **The manual cleanup is 5 rows, not 35.** Of the 35 rows with a workbook Tanking Date and a
   blank list value, **30 were never touched by the Sep 1 run at all** and are fixed *by
   re-running*. Only **5** are genuine per-column failures needing a hand-fix. Do not plan a
   35-row manual pass. (§4)
3. **Never size a run by `Modified`-in-window on this list.** The trigger flow's stuck instances
   have been rewriting `Modified` for three days, so that method undercounts badly — it produced
   a plausible-looking "297 rows" that is off by a factor of three. (§1)
4. **The runbook's "fix in SharePoint, not in Excel" is now wrong** under a parallel run — a
   SharePoint-side fix is overwritten by the next run. (§4)
5. **The reconciliation pass has ≥40 real orphan rows waiting.** Its August deferral reasoning
   has expired. (§5)
6. **A.3/A.4/A.5 are specified but NOT built** — the designer cannot render this flow. The
   mappings in §6 are paste-ready. (§7)

## 1. The Sep 1 run

**`Order Items - Excel Transfer Flow` ran once: 2026-09-01 06:42 EDT (10:42Z), 40m29s, final
status `Failed`.** From the flow's run history in the designer. Its whole history since Aug 21
is that one run; it has not run since.

The `Failed` status is the known false alarm — the action failure propagates up through
Switch → Apply to each while rows still land. **Now confirmed empirically:** that `Failed` run
wrote 913 `Planned Tanking Date` values.

Live counts, whole list, no sampling: `Planned Tanking` 913, `Planned Delivery` 335,
`Location` 211, `Technical Notes` 0, `Info+` 0, n=1052. Zeros on the last two are the signature
of A5 being at 2-of-7 when the run went. Reproduced independently by Track B (22:30) and
Track A (00:1x) — identical numbers.

### The run did NOT process the whole table

`21965-3/4` has 17 versions, last 17.0 @ 2026-08-21T16:36. **No Sep 1 version at all** — the run
never touched it, though the workbook holds Tanking Date 2026-08-24 for it. That is the absence
of a version, not an inference from timestamps.

**Do not size the run by "rows whose `Modified` is in the run window".** That undercounts badly,
and an earlier Track A board post made exactly that mistake ("297 rows"). The trigger flow's
still-running instances have overwritten `Modified` continuously since. 297 is the number of
rows *still showing* a Sep 1 `Modified`; the run actually wrote at least 913.

## 2. The trigger flow is Off, with dozens of runs still in flight

`Order Items - Create or Update Trigger`: **Status `Off`** — turned off for A6 per runbook step
4; step 6 ("turn it back on") never ran because the session was killed. Last *new* run started
Sep 2 08:36 PM.

Filtering run history to `Running`: **29+ instances still going, all started Sep 2 05:23/06:33
AM, each 1d 17–18h elapsed.** (29 was one screen without paging — a floor.) These are what has
been writing to `Order Items` every 1–3 minutes for three days.

In one live run: trigger and all 21 `Initialize variable` actions finish in under 0.4 s, every
stage branch in 0.1–0.2 s, then **one action sits at `1d 10h` — `Condition 1 6 1`**, in the
Finishing/Delivery branch of the 2c auto-stamp.

**Probable cause, NOT confirmed:** throughput throttling from ~900 rows each spawning a
100+-action run. The designer's own banner records this flow being slow 8/22–8/25. Symptom
verified; mechanism is a hypothesis. Deliberately not chased further — the flow is Off, so it
is not hurting anything.

**Decided by the user:** leave it Off, run the backfill (which fills the TextFields as a side
effect), **then** re-enable. When re-enabling, watch that runs actually start and drain — if the
29+ wedged instances are still stuck, turning polling back on may add to a jam rather than
clear one.

### Why app-created rows have blank ID TextFields

All 14 app-created rows (`22156-1/1`, `22157-1/10`…`10/10`, `P00005-1/1`, `P10003-1/2`,
`P10003-2/2`) have `Client_ID_TextField`, `Model_ID_TextField`, `Model_Revision_ID_TextField`
**blank**. Not a fan-out bug — `fanout-powerfx-c2.md` leaves those three to the trigger flow,
which has been off three days. That doc's "Hazard for Track A" section predicted this exactly.

`Order_Number_TextField` **is** populated on all 14 because the fan-out writes it inline (its
"change 4"). **That single decision is the only reason three days of a dead trigger flow has not
shown up as blank Order Numbers on the Production Floor view.** Anything touching the TextField
path must preserve it.

## 3. Is a transfer re-run safe for app-created rows? Yes, today.

**Structural:** the only entry point is `Apply to each` over `TableOrders` rows. Per row:
`Get Order Items` on `Title eq '<Unit ID>'` → Switch `0`→Create, `1`→Update, default→flag.
**No delete, and the reconciliation pass is confirmed not built.** A Unit ID absent from
`TableOrders` is never visited.

**Verified:** all 14 app-created rows have `Modified == Created` with a human `Editor`. None of
the 14 Unit IDs appear in the workbook's `Orders` sheet (1039 non-blank `Order` values, all
unique). A re-run also cannot duplicate them — a duplicate needs the same Unit ID in
`TableOrders`, which is Switch case `1` → Update.

**The clobber is deferred, not absent.** When staff type `22157`/`P10003` into FRM10-12 those
Unit IDs enter `TableOrders` and the flow will Update those rows. Mostly benign. **The one bad
case is a Qty disagreement:** the app fanned `22157` to `/10`; if the workbook says Qty 8 the
flow creates a parallel `22157-1/8`…`8/8` set and the app's ten `x/10` rows become orphans
nothing updates again. Worth a Qty reconciliation check before the pre-cutover run.

## 4. Rows the Sep 1 run missed (A.7)

Method: every live row's `Planned Tanking Date`; the 139 with none; diffed against the workbook.

| Bucket | Count | Meaning |
|---|---|---|
| A — workbook has a date, list blank | **35** | real misses |
| B — both blank | 50 | correct |
| C — in `Order Items`, absent from `TableOrders` | 54 | see section 5 |

**Bucket A is two different problems needing different fixes:**

- **30 rows the Sep 1 run never touched** — last modified 2026-08-21 16:36–16:58, still where
  the Aug 21 test run left them. Confirmed via `21965-3/4`'s version history. **These need the
  re-run, not a hand-fix.**
- **5 rows modified inside the run window** whose Tanking Date did not land. These are the
  genuine per-column failures the runbook predicts. **These are the real A.7 candidates.**

Bucket A with the workbook's value:

```
21499-1/3     2026-08-24   21900-2/8    2026-11-03
21499-1/3 SA  2026-08-24   21900-3/8    2026-11-03
21965-3/4     2026-08-24   21907-1/8    2026-11-04
22045-1/2     2026-08-26   21900-4/8    2026-11-06
21795-1/5     2026-09-14   21946-4/5    2027-01-04
21830-1/5     2026-09-11   21950-2/5    2027-01-05
21795-3/5     2026-09-15   22130-1/3    2027-01-05
21993-8/8     2026-09-15   21926-3/4    2027-01-11
21795-4/5     2026-09-16   21887-2/2    2027-01-14
21795-5/5     2026-09-17   21949-1/5    2027-01-14
21957-7/9     2026-09-30   21949-2/5    2027-01-14
21814-3/11    2026-10-01   21973-3/3    2027-01-27
21843-1/1     2026-10-06   21974-4/5    2027-01-28
21911-2/7     2026-10-15   22142-1/1    2027-02-02
21842-3/5     2026-10-30   22139-2/2    2027-02-26
21906-2/2     2026-11-02   22139-1/2    2027-02-24
21900-1/8     2026-11-03   22138-2/2    2027-02-16
                           22138-1/2    2027-02-11
```

**The runbook's "fix in SharePoint, not in Excel" instruction is now WRONG.** Its reasoning was
that Sep 1 was the last run ever and FRM10-12 would go read-only. That cutover did not happen —
this is a parallel run, staff are still filling the workbook, the flow will run again, and **a
SharePoint-side hand-fix will be overwritten by the next run.**

## 5. The reconciliation pass has real, quantified work waiting

**40 rows exist in `Order Items` whose Unit ID is absent from `TableOrders`** (54 not-in-workbook
minus 14 app-created). `TableOrders.pq`'s `#"Filtered Out Archived Orders"` drops any row the
Archive shows as `Location = AN` or `LI` + delivered — so a cancelled or delivered unit vanishes
from `TableOrders` and a create/update-only flow never sees the transition.

```
21407-2/3, 21786-9/14..14/14 (6), 21787-2/5..5/5 (4), 21789-5/5, 21881-1/2, 21881-2/2,
21923-4/6, 21941-1/3, 21941-2/3, 21944-1/4..4/4 (4), 21965-1/4, 21965-2/4, 21966-1/3,
21968-1/4, 21968-2/4, 22021-1/20,5/20..10/20,12/20,14/20 (9),
22032-1/20,2/20,3/20,5/20,6/20 (5)
```

**Superseded by §5a — the real figure is 71, not 40.** The list above came from the
no-Tanking-Date subset only. It is kept because the individual Unit IDs in it are confirmed;
the *count* is not the total.

## 5a. The full title-level diff — both directions

Full set diff, all 1039 workbook `Order` values against all 1052 live `Order Items` titles.
Intersection **967**. Not a sample.

| Direction | Count | Meaning |
|---|---|---|
| In `TableOrders`, **no** `Order Items` row | **72** | orders that vanish when Order Items becomes source of truth |
| In `Order Items`, **not** in `TableOrders` | 85 → **71** excluding the 14 app-created | stranded rows (§5) |

**These two populations are disjoint by construction** — opposite directions of one diff, so no
row can be in both. Worth stating because it was asked twice.

### The 72 missing rows are NOT a Unit-ID parsing bug

Grouped by order: `22143`(6) `22144`(4) `22145`(2) `22146`(5) `22147`(5) `22148`(4) `22149`(4)
`22150`(8) `22151`(8) `22152`(10) `22153`(4) `22154`(4) `22155`(1) — **65 rows across 13
consecutive order numbers** — plus `20877R1-1/1` and six `P`-prefixed rows (`P1_001-1/1`,
`P1_002-1/1`, `P20001-1/1`, `P20002-1/1`, `P20004-1/2`, `P20004-2/2`).

A Track D investigation from the BO side found 3 of those 6 `P`-prefixed rows and reasonably
inferred a `P`-prefix/underscore matching bug. **The shape of the full 72 does not support
that** — only 6 of 72 have a non-numeric prefix, and a parsing bug would not select 13
consecutive ordinary order numbers.

**The likely cause is that the backfill has simply never reached them.** This fits everything
else here: the Sep 1 run did not complete the table (§1), and `22143`–`22155` are the newest
orders in the workbook.

**So the backfill probably fixes all 72 on its own.** Re-diff after the run before concluding
any matching bug exists — on this evidence there may be none. Whatever survives the run is the
real bug, and the 6 `P`-prefixed rows are where to look first.

The pass was drafted 2026-08-21 and deprioritised the same day because it "only matters once
cancelled/delivered units are actually vanishing from `TableOrders` between runs." **They now
are.** That justification has expired.

## 6. Verified mappings for A.3 / A.5 — specified, NOT yet built

Source keys from a real captured `List rows present in a table` output
(`workflow-data/Excel Table list items raw output.json`); target internals from
`_api/web/lists/getbytitle('Order Items')/fields`. **Nothing retyped from a display name.**

| Target | Internal | Expression |
|---|---|---|
| `Info+` | `Info_x002b_` | `item()?['Info+']` |
| `Technical Notes` | `Technical_x0020_Notes` | `item()?['Technical Notes']` |
| `Protector & Switchgear Item #` | `Protector_x0020__x0026__x0020_Sw` | `item()?['Protector & Switchgear Item _x0023_']` |
| `Configuration` | `Configuration` | `if(or(equals(trim(string(item()?['Configuration'])), ''), equals(trim(string(item()?['Configuration'])), '00:00:00')), null, item()?['Configuration'])` |
| `Section Qty` | `Section_x0020_Qty` | `if(equals(trim(string(item()?['Section Qty'])), ''), null, int(item()?['Section Qty']))` |
| `BO` | `BO` | `if(equals(trim(string(item()?['BO'])), ''), null, string(item()?['BO']))` |

Add each to **both** `CreateOrderItem` and `UpdateOrderItem`.

Three corrections to the runbook's A5 table:

1. **`Info+`'s Excel key needs no escaping — it is literally `Info+`.** The runbook says to
   inspect a test-run JSON to find out; recorded here so nobody has to again.
2. **`Protector & Switchgear Item #` escapes the `#` but not the `&`** →
   `Protector & Switchgear Item _x0023_`. No internal-name collision with
   `Protector & Switchgear PO`, which is `ProtectorSwitchgearPO`.
3. **`Configuration` needs a guard the runbook says it doesn't** — 9 of its 510 non-blank
   workbook values are Excel *time* cells rendering `00:00:00`. `Section Qty` by contrast is
   genuinely clean (119/119 parse); keep its guard anyway.

**`Technical Notes` is not "plain, no special characters"** — all 7 non-blank values are raw
SharePoint HTML that already round-tripped out of SharePoint once. Target is a `Note` field.
Flagged, not fixed; stripping HTML is a data decision.

**`BO` passes through exactly as stored.** Per the user: derived-by-default but **manually
overridable, and 7 units deliberately differ from the derived value.** Do not compute it, do not
add a derive-and-compare guard — either silently reverts those 7.

### Expected counts, to verify a future run against rather than eyeball

From `FRM10-12_2026-09-01_13h43m.xlsx` (1039 rows): `Info+` 97, `Technical Notes` 7,
`Protector & Switchgear Item #` **0**, `Configuration` 510 (501 guarded), `Section Qty` 119,
`BO` 626.

**`Protector & Switchgear Item #` is 100% blank at source.** A6's acceptance test "the 5 new
columns are populated not blank" is impossible for it and will look like a failure when it is
the correct result. Verify that one by confirming the mapping exists, never by counting.

## 7. Still unverified — do not skip when the designer is usable

- **A5b (stated run-blocker):** confirm `Tanking End Date`, `Tanking Status`, `Delivery End
  Date`, `Delivery Status` are not mapped on either action. Internal-name trap: they are
  `TankingDate` / `DeliveryDate` — the internals **drop "End"**.
- **A5c:** the `toLower()` fix on the six mapped stages.

Both blocked by the designer failing to render `Apply to each` — reproducible in the new
designer and the classic (`?v3=false`) designer alike, almost certainly the cost of drawing
`CreateOrderItem` + `UpdateOrderItem` with ~90 field mappings each.

### ⚠️ The designer is blocked, but RUN HISTORY IS NOT — use it to inspect this flow

**Confirmed 2026-09-04.** The run detail page **paginates iterations one at a time** — it shows
`Show [1] of 256` and renders a single iteration's actions. The editor renders **all ~90 field
mappings on both write actions at once**, which is what pegs the page. So:

| Surface | Works on this flow? |
|---|---|
| Editor canvas (`Apply to each` expanded) | ❌ hangs, both designers |
| **Run history → run detail → iteration** | ✅ **renders fine** |
| Run detail → action → *Show raw inputs* / outputs | ✅ full JSON body |

**This makes run history a usable inspection surface whenever editing is blocked.** It is how the
Date-Only-vs-Date-and-Time question was settled without a test run: open a small run (the Aug 21
tests are ~10 min, not 40), expand `Apply to each` → `CheckOrderMatch` → `Switch` → the taken
case → the write action, then *Show raw inputs* for the literal payload.

**Prefer a small/old test run over the big one** — the Sep 1 run has ~1000 iterations; the Aug 21
test runs are far lighter and carry the same expressions.

**What run history can and cannot tell you.** The **outputs** body is SharePoint's response after
the write, so it reveals the *stored* value and the column's type as SharePoint reports it. The
**inputs** body is what the action sent. Don't cite an outputs body as evidence of what the flow
sent, or vice versa — the two answer different questions.

Also: running an instant flow uses the **Run button on the flow's detail page**, not the canvas —
so a *run* is possible even while *editing* is blocked. That distinction was initially missed and
it matters, because it means a date-correcting backfill is not gated behind this blocker.

## 8. Other doc corrections this forces

**PnP being blocked does not mean schema changes are blocked.** Track B created 19 columns via
site-context REST (`POST .../fields/createfieldasxml` with a digest from `_api/contextinfo`),
19 for 19, in about two minutes. `order-items-manual-build-checklist.md`,
`order-items-build-plan.md`, `roadmap.md` and the cutover runbook all imply an hour of clicking.
`AADSTS700016` is about a third-party multi-tenant AAD app, not schema changes.

---

## 9. The flow definition, read from the export — 2026-09-05

Everything in §7 that was "unverified — do not skip" is now answered, and answered **without
touching production**. The flow was exported as a `.zip`; `Microsoft.Flow/flows/<id>/definition.json`
carries the whole definition. Both files are in `workflow-data/`.

**This section supersedes §7 for anything it covers, and supersedes every "fixed on Aug 18" claim
anywhere in this repo.**

### 🔴 9.1 The `toLower()` guard was never applied

`cutover-runbook-2026-09-01.md` §D0 diagnosed the failure at **01:45 on Sep 1**, five hours before
the run, and wrote the fix down as an instruction — *"The fix — apply to all six mapped stages"*.
Nothing records it as carried out, and the export proves it was not.

| | Count |
|---|---|
| `toLower(` in the entire definition | **4** |
| …and all four are on | `Tanking` / `Delivery` — the two stages that are **not mapped** |
| Uppercase `'EC'` literals | **24** |
| Mapped stages carrying `toLower()` | **0 of 6** |

The live text on all six is still case-sensitive:

```
CoilingStatus  @if(equals(trim(item()?['Coiling Date']), ''), null,
                  if(equals(trim(item()?['Coiling Date']), 'EC'), 'In Progress', 'Completed'))
CoilingDate    @if(or(equals(trim(item()?['Coiling Date']), ''),
                      equals(trim(item()?['Coiling Date']), 'EC')),
                  null, addDays('1899-12-30', int(item()?['Coiling Date'])))
```

**Why the failure surfaces as a `Switch` error.** `Switch` branches on
`length(outputs('Get_Order_items')?['body/value'])`:

| Case | Action |
|---|---|
| `No_Items_Found` | `CreateOrderItem` |
| `One_Item_Found` | `UpdateOrderItem` |
| default | `DuplicateOrderItem` |

The stage-date mappings live **inside** those two actions, so a row hitting `int('ec')` throws
there and surfaces as `Action 'Switch' failed` — the same error the Sep 1 run reported.

⚠️ **What is proven, and what is not.** Proven: the guard is case-sensitive, lowercase `ec` exists
in the source, `int('ec')` throws, and that throw presents as `Action 'Switch' failed`. **Not**
proven: that iteration **497 specifically** was one of those rows. The workbook has been refreshed
four times since Sep 1 and Power Query rebuilds `TableOrders`, so row order then and now are not
comparable — in the 09-04 snapshot the first `ec` row sits at position ~63, not 497. One page of
run history (Sep 1 run → iteration 497 → `Switch` → raw inputs) would settle it. **It changes
nothing about the fix**, which is required either way.

**The fix is 24 expressions** — 6 stages × `{Stage}Status` and `{Stage}Date`, on **both** write
actions: `equals(trim(X), 'EC')` → `equals(toLower(trim(X)), 'ec')`. It outranks the five parity
columns of §6: those are cosmetic and on no staff view; this one decides whether the run completes.

### ✅ 9.2 The Excel source is correct after the move

| | |
|---|---|
| Live `inputs/parameters/table` | `{72371618-48E3-4FA4-B667-3B76BFA2D42A}` |
| Live file | `/General/FAB/Revue/Formulaires/FRM10-12.xlsx` |
| Stale, in `metadata` only | `/General/FAB/Revue/FRM10-12.xlsx`, table `{5C992B17-…}` |
| `paginationPolicy/minimumItemCount` | **5000** |

The old path and table id survive as connector cache and are harmless — read
`inputs/parameters`, never `metadata`.

### ✅ 9.3 The mappings survived the re-point, but were never symmetric

| Action | `item/` fields |
|---|---|
| `UpdateOrderItem` | **58** |
| `CreateOrderItem` | **50** |
| `UpdateOrder` | 5 |
| `Update_item` (Model Revisions) | 2 |

The 8-field gap is **exactly** the `{Stage}StartDate` set, and on `UpdateOrderItem` all eight are
`@null`. So the asymmetry is cosmetic — one action explicitly nulls them, the other omits them,
same stored result. **This is what preserves the blank-`{Stage} Start Date` marker** the
Tanking/Delivery remediation keys on (§ the roadmap's "single biggest data problem"). Nulling costs
nothing: **1 of 1052 rows** carries any Start Date, `Coiling Start Date = 2026-09-02T08:03:52Z`,
which is a trigger-flow stamp rather than anything a human typed.

### ✅ 9.4 §6's five columns are confirmed still absent

Absent from **both** write actions: `Info+`, `Technical Notes`, `Configuration`, `Section Qty`,
`Protector & Switchgear Item #`, `Order_Number_TextField` and `BO`. §6's mapping table stands.

### ✅ 9.5 The two side-writes, exactly as documented

- **`UpdateOrder`** writes precisely the five companion columns — `EngineeringRequired`, `LDs`,
  `ClientDateStatus/Value`, `SalesNotes`, `OrderStatus/Value`. **Decision 2026-09-05:** they stay
  for this run so the values land, then **both these and the BO mapping are removed** — after the
  cutoff the SharePoint list is the reference, and leaving them in makes every future run overwrite
  SharePoint-native edits with stale Excel values.
- **`Update_item`** writes `Family/Value` and `ModelName` to `Model Revisions`. So the flow *does*
  write `Family`, which makes the Choice's fill-in setting a live failure mode independent of §9.1.

### 9.6 Correction — `Model Revisions.Family` is not junk

An earlier claim in this session put ~28% of `Family` at legacy numeric junk (`91`, `1234`,
`46264`) and made it the iteration-497 suspect. **Measured against the 2026-09-05 export that is
wrong.** The live column holds `C` 34 · `B1` 19 · `A` 7 · `B2` 2 and **329 blank — no numeric
values at all**. The column is clean and sparse, not dirty. What it needs is the fill pass
(roadmap item 25), not a cleanup.

### 9.7 Re-scan of the workbook the next run will read — 2026-09-04 23:08

D0 scanned the 08-31 snapshot, found 9 marker rows (3 lowercase) and predicted the count would
grow. Re-scanned `live-workbook-data/FRM10-12_2026-09-04_23h08m.xlsx`, `TableOrders` `B5:CE1024`,
1,019 data rows — the refresh the flow will actually read:

| | 08-31 (D0) | **09-04** |
|---|---|---|
| Marker rows in the six mapped stages | 9 | **10** |
| …lowercase `ec`, i.e. **will throw** | 3 | **6** |
| …uppercase `EC`, guarded today | 6 | 4 |

**Every marker is in `Coiling Date`.** The other five mapped stages are clean, and so is every
other `int()`-bound column — `Tanking Date`, `Delivery Date`, `Section Qty`, `Time (days)`,
`Tank Delivery Date`, `Original Tanking Date`, `Manual Estimated Delivery Date`. So `Section Qty`'s
guard really is belt-and-braces rather than load-bearing, as A5 assumed.

The six rows that will fail, by workbook position (**not** iteration number — see the warning in
§9.1):

| Position | Unit |
|---|---|
| ~63 | `21821-1/1` |
| ~174 | `21795-3/5` |
| ~192 | `21995-1/2` |
| ~235 | `21833-1/6` |
| ~253 | `21387-5/6` |
| ~284 | `21957-7/9` |

**The lowercase count doubled in four days**, which is the point: this is staff typing `ec` into a
live column, not a fixed set of legacy rows. Hand-fixing the six would work today and be wrong
again next week. Apply `toLower()` to all six stages even though only `Coiling Date` carries
markers right now — nothing stops the same typing appearing in `Stacking` or `Drying` tomorrow.

Scanner kept at `scratchpad/ec_scan.py`; point it at any newer snapshot. Note that it treats real
`datetime` cells as fine — the Excel connector hands those to the flow as serial numbers, which is
what `addDays('1899-12-30', int(...))` is built for. Only a genuine *string* in a date column is a
landmine.
