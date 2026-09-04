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

**This is a floor, not a total** — derived from the no-Tanking-Date subset only, so orphans that
do carry a Tanking Date are not counted. A full title-level diff would give the real number.

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

## 8. Other doc corrections this forces

**PnP being blocked does not mean schema changes are blocked.** Track B created 19 columns via
site-context REST (`POST .../fields/createfieldasxml` with a digest from `_api/contextinfo`),
19 for 19, in about two minutes. `order-items-manual-build-checklist.md`,
`order-items-build-plan.md`, `roadmap.md` and the cutover runbook all imply an hour of clicking.
`AADSTS700016` is about a third-party multi-tenant AAD app, not schema changes.
