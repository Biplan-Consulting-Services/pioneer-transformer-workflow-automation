# Nightly Sync: review of the user's hand-built flow, and the proposed v002

Written 2026-09-25 ~01:00 by the planning session, while the user slept. Source: the user's export, taken into
versioning as `workflow-data/Order Items - Nightly Sync/v001` (pulled 2026-09-24 23:18). **Nothing in the
tenant has been changed.** The flow the repo generated on 09-16 (`workflow-data/nightly-cleanup/`,
`gen_nightly_cleanup.py`) was never deployed; this hand-built flow is the one that exists.

---

## 1. What v001 does

Trigger: **Recurrence, daily, `startTime 2026-09-15T05:00:00Z`**, i.e. 01:00 EDT (00:00 EST once DST ends; see §3.6).

```
Get_items                      ALL Order Items (1,127), no filter, no $select, pagination 5000
List_rows_present_in_a_table   an Excel table (columns Order / Location / Delivery Date: the archive), pagination 5000
Apply_to_each  over ALL 1,127 units, SEQUENTIAL
   Filter_array                  Excel rows where Order = this unit's Title
   Condition_1                   Excel Delivery Date blank?  -> do nothing
     else  Set vLivraison        = Excel Location == 'LI'
           Set vDateLivraison    = Excel Delivery Date (serial) <= today - 7 days
           Condition             both true -> DELETE the Order Items row   else -> Compose(Title)
```

**The rule it implements:** delete a unit from Order Items once the Excel archive says it was delivered (`LI`
with a delivery date) at least 7 days ago. That is the 09-16 grace rule (7 days, clock = the delivery date),
and the reconfirm-against-Excel step `archiving-plan.md` requires. The intent is sound.

## 2. Why it "runs forever"

| cost driver | v001 | why it hurts |
|---|---|---|
| units visited | **all 1,127**, every night | only units at Livraison with an old delivery date can ever qualify: about 100 today |
| actions per run | **~6 per unit ≈ 6,800**, plus paging | above a flow's daily Power Platform request allowance (09-11 estimate: ~2,000/day on this licence). Past it, Power Automate **throttles**: runs don't fail, they slow to a crawl. That is the "indefinitely" |
| loop mode | **sequential** (forced by `Set variable` inside the loop) | no parallelism possible while loop variables are used |
| Excel read | up to 5,000 rows, **every row** | slow connector, paged at 256; and the per-unit `Filter array` rescans all of it 1,127 times |

## 3. Correctness and safety findings

1. **It trusts the Excel row alone.** Nothing checks the Order Items row's own state before deleting it: its
   `Location`, its `Item Status`, its own `Delivery End Date`. If the archive row is wrong, stale or hand-edited,
   a live unit is deleted.
2. **No cap and no dry run.** A bad Excel read (a wrong table, a broken refresh, a mis-keyed column) could delete
   every matching unit in one night. Deleted items go to the **site recycle bin (93 days)**, so this is
   recoverable by hand, one item at a time, but nobody would be told it happened.
3. **No record of what it deleted.** The only output is a `Compose` on the *keep* branch. The run history is
   the only trace, and it rotates.
4. **The 5,000-row pagination ceiling.** `TableArchiveFRM10_12` held **5,120 rows** on 09-04 and grows. Rows past
   5,000 are never read. That fails *safe* (those units are never deleted), but silently. Filtering the Excel read
   to `Location = LI` (§4) keeps it far below the ceiling.
5. **What deletion loses.** `analytics-history-options.md` (WS-092) found that the 24 per-unit stage columns
   (start/end/status per stage) are **not** in the Excel archive, so deleting a unit loses its production timeline.
   🟢 **Since tonight this is partly covered:** the mirror snapshots (`docs/change-tracking-design-2026-09-24.md`)
   hold every full row for 30 days, then monthly forever, and the change journal records each deletion. The
   durable per-unit completion record is design decision D4 ("later, from the journal").
6. **DST.** `05:00Z` is 01:00 EDT now, but **00:00 EST after 2026-11-01**. That is the same minute as midnight
   `TODAY()` rollover, which is the wrong moment for stage B below. Use the recurrence's `timeZone`
   (`Eastern Standard Time`, hours `[1]`) instead of a UTC start time.
7. **Orders are left behind.** When all of an order's units are deleted, its `Order` row stays (the 09-16 order
   22021 case). That is fine under "keep the Order", but it should be a decision.

## 4. What is missing: the TODAY() recalculation

v001 does **not** touch rows for the calculated columns. `Estimated Delivery Date` on Order Items uses
`MAX(TODAY(), …)` on its stage branches, and a SharePoint calculated column only recomputes when the row is saved.
So a *stalled* unit's estimate freezes on the day it was last saved.

**Measured from the mirror, 2026-09-24 23:11:** of **1,104 Active** units, **1,068** have a fixed Planned or Manual
delivery date (a branch that never calls `TODAY()`), 23 are on a future-dated branch, 9 have no milestones, and
**only 4 are on a `TODAY()` branch right now**. So the nightly touch should write **about 4 rows**, not 1,100.
The 09-16 generator already has exactly this stage (B1–B4: filter to Active with no Planned/Manual date, then a
`Filter array` for "TODAY() wins", then touch `CalcRefreshed`).

⚠️ `test calculated column` (`MAX(TODAY(), [Planned Delivery Date])+7`) is still on the list and also depends on
`TODAY()`. Delete it (it is on the 09-21 loose-ends list).

## 5. Proposed v002: same intent, ~100× cheaper, safe by default

```
Recurrence       daily, timeZone "Eastern Standard Time", 01:30 (after the 01:00 midnight rollover settles)

B  RECALC   (from gen_nightly_cleanup.py stage B)
   B1 Get items   $filter  ItemStatus eq 'Active' and Planned Delivery Date eq null and Manual EDD eq null   (~36 rows)
   B2 Filter array   rows where the formula's branch is TODAY()-derived (milestone in the past)              (~4 rows)
   B3 Apply to each (concurrency 10)  Update item: CalcRefreshed = utcNow()

C  ARCHIVE DELETE   (the user's rule, made cheap and safe)
   C1 Get items   $filter  Location eq 'Livraison' and DeliveryDate le '<today − 7>'   $select Id,Title,ItemStatus,DeliveryDate   (~100)
   C2 List rows   Excel archive, filter  Location eq 'LI'   (well under 5,000)
   C3 Select      Excel rows → {Order, DeliveryDate}   (one pass, no per-unit rescan)
   C4 Filter array  candidates whose Title is in C3 AND whose Excel delivery date is also ≤ today − 7
   C5 GUARD   if count(C4) > 50 → do NOT delete; compose "cap exceeded: N candidates" and stop
   C6 Apply to each (concurrency 10, NO variables)
        if DeleteEnabled:  Delete item   else:  compose "would delete <Title>"
   C7 Compose summary:  B touched N · C candidates N · deleted N · held back N, with Titles
```

- **Two independent confirmations before any delete:** Order Items itself says Livraison + an old delivery date,
  **and** the Excel archive says `LI` + an old delivery date. v001 had only the second.
- **Actions per night:** B ≈ 4–10, C ≈ 3 × ~100 ≈ 300. Total ≈ **300–400**, down from ~6,800.
- **`DeleteEnabled` starts `false`** (a dry run that names what it *would* delete), then flips to `true` after
  one night's report has been checked against the mirror.
- **`Stage A` (mark Delivered) is not needed.** The trigger flow (v006/v008 `CompletOrder`) already sets
  `Terminé`/`Delivered` when a unit reaches Livraison.
- **The trigger-flow interaction.** B's touches fire the Order Items trigger flow about 4 times a night. That's
  harmless: the loop is fixed. Deletes do not fire a "created or modified" trigger.
- It is **authored locally** with the generator, as `v002` of `Order Items - Nightly Sync`, parent `v001`, and
  staged for the user to paste. Nothing goes live without them.

## 6. Decisions for the user

| # | question | proposed |
|---|---|---|
| N1 | Deletion stays the plan? (The 09-16 design recommended *not* deleting; your flow deletes. With the mirror snapshots now holding every deleted row, deletion is much safer than it was on 09-16) | yes, with v002's double confirmation, cap and dry-run start |
| N2 | The cap for one night | 50 units |
| N3 | Run time | 01:30 Eastern (DST-proof) |
| N4 | Orders whose units are all deleted: keep the Order row? | keep, as today |
| N5 | Turn v001 off until v002 is ready? It is expensive and deletes on Excel alone | your call. If it stays on, the mirror now records whatever it deletes |

## 6a. 🔴 CORRECTION (01:2x): v002 cannot work on today's list, so v003 replaces it

Found by `claude-5b` through the new catalog `fillRate` (E8c), and confirmed from the mirror by the planning session:
**`Delivery End Date` (`DeliveryDate`) is EMPTY on all 1,127 units**, and so are `Delivery Start Date` and
`Delivery Status`. **Only 23 units are at `Livraison`, all already `Delivered`.** Staff record the delivery date
**only in the Excel archive**, not on the unit. So v002's C1 (`Location eq 'Livraison' and DeliveryDate lt …`) matches
**0 rows every night** and can never delete anything. That fails safe, but it defeats the purpose. It also means §2's
"~100 candidates" and §5's "C ≈ 300 actions" were wrong: the 09-16 design assumed `DeliveryDate` is written at
delivery, and I carried that over without checking today's data. The real candidate count is about 23.

**v003 — STAGED 01:13 in `_outbox/PASTE-ME.json` (`gen_nightly_sync.py`, 14/14 mutation tests; reviewed) — changes C1 to `Location eq 'Livraison' and ItemStatus eq 'Delivered'`** (the trigger flow's
`CompletOrder` sets `Delivered`), and takes the 7-day clock from the Excel Delivery Date alone. It adds a new
report-only list: **units the Excel archive calls done ≥ 7 days ago that Order Items does NOT show as
Livraison + Delivered.** v001 deletes exactly those on Excel's word alone, so this list is the evidence for N1.
v003 is still `DeleteEnabled = false`.

Other options the user can pick instead:
- (b) the Planned Delivery Date as the clock. Not recommended: it is the plan, editable after the fact.
- (c) make delivery write `Delivery End Date` (a process or flow change), then keep the v002 logic.

## 6b. v002 (withdrawn) — the paste/test steps below apply unchanged to **v003**

Generated by `scripts/gen_nightly_sync.py` (`claude-5b`, E11); reviewed by the planning session; snapshotted as
**v002 (`local`, parent v001)** and staged in `workflow-data/Order Items - Nightly Sync/_outbox/PASTE-ME.json`.
`test_gen_nightly_sync.py`: 11 unsafe mutations each abort the generator (variables in a loop, the cap removed,
DeleteEnabled on, pagination under 5000, the Excel ids changed, a UTC startTime, a connection reference dropped…).

Two deviations from §5, both correct:
- C1 filters `DeliveryDate lt '<Eastern today − 6>'`. Delivery dates are stored at Eastern midnight (`T04:00Z` /
  `T05:00Z`) and a bare OData date means UTC midnight, so `le '<today − 7>'` would silently skip everything delivered
  exactly 7 days ago.
- No `$select` on C1: the connector's Get items has no such parameter.

**Before you paste, two things to know:**
1. **Both connections in v001 are plain connections, not solution connection references**
   (`shared_sharepointonline` → `…98111a58…`, `shared_excelonlinebusiness` → `…2cd3888f…`). So v001 is probably not
   in the solution. v002 keeps them as they are, which is right for pasting into v001's own flow. If you want it in
   the solution later, that is the same move the trigger flow needed.
2. **SA twin units are never deleted by this.** The Excel archive has only the regular unit ids, so `21665-1/3 SA`
   and the like will appear in the summary's *held back* list. Decide whether SA twins should follow their regular unit.

**Paste and test:**
1. Paste `PASTE-ME.json` into the **existing** `Order Items - Nightly Sync` flow (extension, editor wrapper), save,
   and copy the JSON back into `_inbox/` so the hash confirms v002.
2. Leave `DeleteEnabled = false` (the `Settings` action). Run it once manually, or let 01:30 run it.
3. Read `C7_Summary`: B touched ~4, C candidates, confirmed by Excel, held back, and the "would delete" titles.
   Compare with the mirror. The planning session can do this in 30 s from a refresh.
4. Only then set `DeleteEnabled = true` (a one-value edit in `Settings`), after answering N1–N5.

## 7. Tonight's run

v001 was due at 05:00Z (01:00 EDT) on 2026-09-25. A full mirror snapshot was taken at **00:55**
(`snapshots/2026-09-25_0055`), before it. What it deletes will show as `deleted` events in the next journal, and is
reported on the build-night board.
