# Cutover runbook — build night 2026-09-01, hard cutover 2026-09-02

**Goal**: staff stop editing FRM10-12 and start working in SharePoint on 2026-09-02.
FRM10-12 becomes the read-only `viewer/` mirror.

**Status of this doc**: written 2026-09-01 from a fresh read of both repos
(`Workflow-Automation`, `FRM10-12`), not from memory. Every "already built" claim below is
sourced to the doc or query that records it.

**User's decisions, 2026-09-01** (these shaped the plan, don't re-litigate them):
- Hard cutover is the target; re-evaluate only if a gate below fails.
- The 5 `Models` fields get built **tonight**, not deferred.
- Production-stage automation comes **out** of the trigger flow (Monday.com takes it over),
  but a disabled copy is parked as a fallback.
- TextField sync (and anything else per-row) folds **into the transfer flow**, so big batch
  transfers don't depend on the create/update trigger firing ~1000 times.

---

## Gate 0 — Request budget. Do this first, before any building.

The last bulk attempt ran **~350 flows instead of the expected ~1000**. Treat this as the
top risk to the whole cutover, not a curiosity.

**Hypothesis**: this is a Power Platform *request* quota, not a flow defect. The platform
meters actions, not runs. `Order Items - created or updated trigger` does roughly 17 actions
per row (TextField sync + 16 stage stamps + the advance-to-Pending chain). 350 × 17 ≈ 5,950
— and Office 365 *seeded* licences are commonly capped around **6,000 Power Platform
requests / 24h**, against ~40,000 on a standalone Power Automate per-user plan. The
arithmetic lands close enough to be worth 15 minutes of verification.

**Verify (don't assume)**:
1. Power Platform admin center → Analytics → Power Automate → requests / throttling report.
2. The failed batch's run history: look for HTTP **429** or `ActionThrottled`, versus runs
   that simply never fired.
3. Confirm which licence the flow owner actually holds.

**Why it matters tonight**: if the cap is real, the budget must be spent on the *final run*,
not on testing. Consequences, applied throughout this plan:
- Test against a **10-row slice**, never the full table.
- The full-scale run happens **once**, last, after everything else is verified.
- If several sessions are running in parallel (see "Working in parallel" below), only **one**
  of them triggers flow runs.

**If the cap is confirmed and tight**: request a licence uplift before tomorrow, or split the
final run across two calendar days (rows 1–500 tonight, the rest after the quota window
rolls). That second option is compatible with a hard cutover only if the reconciliation pass
runs after the *second* half.

---

## Gate 1 — Pre-flight checks (15 min)

- [ ] **Pagination threshold on the transfer flow is back to `5000`.** It was lowered to `10`
      during testing, and `order-items-power-automate-flows.md` flags confirming this before
      any real run. At `10` the final sync silently transfers 10 rows.
- [ ] **Nobody has FRM10-12 open in Excel Online.** Per `FRM10-12/CONTEXT.md`, co-authoring
      during a refresh is what corrupted the `TableOrders` binding on 2026-08-28. Refresh from
      desktop Excel with the file closed to everyone else.
- [ ] **Never a generic Refresh All / COM `RefreshAll`** on FRM10-12 — use the Office Script
      button on the `Orders` sheet. Native formula columns get wiped otherwise.
- [ ] Take a fresh snapshot into `FRM10-12/live-workbook-data/`. This is the rollback artifact.

---

## Step 1 — Schema: the 5 Models fields onto Order Items

**Blocks steps 2d, 5 and 6. Do it first.**

Add to `Order Items` (SharePoint UI — PnP PowerShell is still blocked on this tenant):

| Column | Type | Notes |
|---|---|---|
| `Technical Notes` | Multiple lines of text | `Models.Notes` today |
| `Info+` | Single line of text | |
| `Protector & Switchgear Item #` | Single line of text | |
| `Configuration` | Single line of text | |
| `Section Qty` | Number | |

Types must match `viewer/power-query/ColumnMap.pq`'s `Type` codes exactly
(text/text/text/text/**number**), or `ApplyColumnMap`'s retype step misbehaves downstream.

**Rationale** (user's 2026-08-31 call, recorded in `ColumnMap.pq`): `Models` should stay a
lightweight linking/engineering-tracking list, not a home for fields of unclear grain.

**The backfill is free — there is no separate backfill pass.** All five already exist as
populated columns in raw `TableOrders` (they're in `TableOrdersColumnOrder.pq`'s frozen
layout, fed by the old Models merge). The transfer flow maps them like any other Excel column
in step 2d, and the final sync populates them.

**Do NOT add the ColumnMap rows yet** — that happens in step 5, after the columns exist live.

---

## Step 2 — Flow rework

The long pole. Sub-steps in dependency order.

### 2a. Park the stage-stamping fallback (5 min, before 2b)

In Power Automate, **Save As** on `Order Items - created or updated trigger` →
`Order Items - stage stamping (FALLBACK, do not enable)`. Save As produces a **disabled**
copy by default — confirm it's off and leave it off.

Insurance against Monday.com not working out. Costs nothing while disabled.

### 2b. Strip production-stage stamping from the live trigger flow

Remove from `Order Items - created or updated trigger`:
- the 16 `{Stage} Start Date` / `{Stage} End Date` stamps
- the `N/A` status handling and the advance-to-Pending chain

Built and tested 2026-08-14; retired because production tracking moves to Monday.com
(roadmap workstream 5). This is the bulk of the ~17 actions/row driving Gate 0's ceiling.

**Confirm before stripping**: that Monday.com is actually receiving production data. If it
isn't yet, there's a window between cutover and Monday going live where *nothing* tracks
stage progression — in which case re-enable the 2a copy rather than leaving a gap.

### 2c. Fold TextField sync into the transfer flow

Move the Lookup → TextField companion writes out of the trigger flow and into the transfer
flow's own `CreateOrderItem` / `UpdateOrderItem` actions.

**Why this is strictly better, not just cheaper**: the transfer flow *already* resolves
`ClientIdToWrite` / `ModelIdToWrite` / `ModelRevisionIdToWrite` (built 2026-08-20/21,
including SA disambiguation). Writing the companion TextField in the same `Create item` /
`Update item` action costs **zero additional requests** — it's another field on an action
that's already happening. The separate trigger-flow round-trip was pure overhead.

**Keep the trigger flow alive afterward** — it's still needed for *manual* edits staff make in
SharePoint from tomorrow on (someone changes a Lookup by hand, the TextField must follow). It
just stops being the mechanism for bulk transfers.

**These fields now have real consumers.** The 2026-08-19 assessment found zero confirmed
consumers of any `_TextField`, and the viewer dropped its last reference on 2026-08-31. Step 3
changes that: SharePoint cannot filter or group through a Lookup, so any view filtering on
Client/Model/Order Number needs the TextField companion. Accurate TextFields become
load-bearing tomorrow.

### 2d. Map the 5 new fields in the transfer flow

Add to both `CreateOrderItem` and `UpdateOrderItem` (kept in sync field-for-field):

```
Technical Notes                -> item()?['Technical Notes']
Info+                          -> item()?['Info+']
Protector & Switchgear Item #  -> item()?['Protector & Switchgear Item #']
Configuration                  -> item()?['Configuration']
Section Qty                    -> int() / float() with a blank guard
```

**`Section Qty` needs the standard guard.** Per the hard-won 2026-08-18 lesson in
`order-items-power-automate-flows.md`: check for non-numeric status markers (`EC`, and
possibly `AT`/`RE`/`BO`/`TE`/`B1`–`B3`) and for blank before `int()`. An unguarded `int()` is
exactly what failed at iteration 114 on the stage dates.

**Verify the four text fields are clean first** — spot-check the raw column values in the live
workbook rather than assuming. `indéterrminé` / `CONFRIMED` / `EC` have all turned up in
supposedly-clean columns on this data before.

### 2e. Reconciliation pass — now mandatory

Deferred on 2026-08-21 to "the pre-final-migration pass". **A hard cutover is that pass.**

The full Steps 0–4 walkthrough is already drafted in `order-items-power-automate-flows.md`:
track this run's processed Unit IDs in an array variable → pull currently-`Active`
`Order Items` rows → diff against the array → resolve the Archive file via the `Index` list
(same as `ImportFromIndex.pq`) → finalize `Cancelled`/`Delivered`, or flag an unresolved miss.

**Check whether it's genuinely unbuilt before building it.** The last two "not yet built" items
in that doc both turned out to already exist. Open the flow and look.

**Why it can't be skipped tomorrow**: `TableOrders.pq` filters cancelled/delivered rows out
once archived, so the transfer flow can't react to what it no longer sees. Without this pass,
`Order Items` keeps `Active` rows for units that are actually done — and from tomorrow there's
no Excel side left to correct them from.

### Not tonight — deliberately cut

- **`Order Items.BO` column + BO sync flow.** The viewer takes `BO` from `BO Manager.xlsx`
  directly via `BackOrders.pq`, so it is **not** on the viewer's critical path. It only feeds
  the in-SharePoint Estimated Delivery Date penalty, which the spec itself measures at 8 of
  ~1000 rows and rates low priority.
- **Estimated Delivery Date computation on Order Items** + its daily sweep. Spec'd 2026-08-31
  and ready, but the viewer keeps `Estimated Delivery Date` as a native Excel formula
  (excluded from `TableOrdersColumnOrder`), so nothing tomorrow depends on it.
- **Phase 1 / `Workflow Tasks`** (all 8 checklist steps). Not started, not a cutover blocker.

---

## Step 3 — Views (parallelisable, no flow dependency)

The cleanest work to hand to a second session — pure SharePoint UI, touches no flow and burns
no request budget.

**`Order Items` → `Production Floor`** (spec already written in
`order-items-manual-build-checklist.md`, "Production-floor view"):
- Columns: `Unit ID`, `Order_Number_TextField`, `Location`, `Item Status`, `Coil Winder`,
  `Manual Estimated Delivery Date`
- Filter: `Item Status = Active`
- Group by `Location` (this is the production step staff already read)
- Sort within group: `Manual Estimated Delivery Date` ascending
- Format this column → Choice column colors on `Location`; try a **Gallery** view for cards

**`Order Items` → `Planning`**: the columns staff use in `TableOrders` today, in that order, so
the SharePoint list is legible to someone used to the workbook. `TableOrdersColumnOrder.pq` is
the exact list to mirror.

**`Order`**: already done — all four calculated columns are live in the **All Items** view as of
2026-08-31 (`FX Rate` deliberately excluded as an internal helper). Nothing to do.

**Dependency worth stating**: any view that filters or groups on Client/Model/Order Number
depends on step 2c's TextField accuracy. Build the views, but verify them *after* the final
sync, not before.

---

## Step 4 — The final sync

**Only after steps 1, 2 and 3 are done and spot-checked on the 10-row slice.**

1. Freeze: confirm nobody has FRM10-12 open. Announce it.
2. Snapshot the workbook into `live-workbook-data/`.
3. Refresh FRM10-12 via the Office Script button (never Refresh All) so `TableOrders` is current.
4. Confirm pagination threshold is `5000`.
5. **Turn OFF `Order Items - created or updated trigger`** for the duration of the run. The
   transfer flow now writes the TextFields itself (2c), so the trigger flow would only add
   ~1000 redundant runs against the Gate 0 budget. Turn it back on immediately after.
6. Run the transfer flow, full table.
7. Run the reconciliation pass.
8. Re-enable the trigger flow.

**Acceptance checks before calling it done:**
- [ ] Row count: `Order Items` vs `TableOrders` (~980) vs the 1038 currently in the list. The
      three sets are known not to coincide — account for the difference, don't wave it off.
- [ ] The 5 new fields are populated, not blank.
- [ ] TextField companions are current on a sample of rows (real staleness gaps were found
      here on 2026-08-31).
- [ ] The reconciliation pass's unresolved-miss count is zero, or every miss is explained.
- [ ] No 429 / throttling in the run history.

---

## Step 5 — Viewer transfer

1. Add the 5 `Order Items` entity rows to `viewer/power-query/ColumnMap.pq`, and delete the
   `PENDING` comment block (~line 121) plus the five `Models` "Reference only" rows they
   supersede. Types: text, text, text, text, number.
2. `viewer/scripts/Sync-PowerQuery.ps1` to push the M into `viewer/workbook/FRM10-12.xlsx`.
   **Close the workbook first** — a 2026-08-31 apply silently failed against a file lock and
   was only caught by re-running a dry run. Re-run the dry run and confirm all queries report
   *Unchanged*.
3. Refresh the viewer. Confirm the 5 columns now populate instead of rendering null.
4. **Parity check against today's FRM10-12**: same columns, same order, same row count.
   `TableOrdersColumnOrder.pq` is frozen to the live post-corruption-repair layout precisely so
   staff see no difference.
5. Deploy: put the viewer where staff will open it; make the old FRM10-12 read-only so nobody
   edits it out of habit tomorrow.

**Known cosmetic gaps, not regressions** — don't chase these tomorrow: `Duplicate` and
`Duplicate Order` read blank by design; `Item Status` is deliberately not in the layout.

**Worth a look while you're in here** (not a blocker): `viewer/TableOrders.pq` defaults a
missing `Lead Time` to **26**, while the Estimated Delivery Date spec reads **52** off the
workbook's `XLOOKUP(..., 52)`. Two different computations, possibly both faithful — but the
same field with two defaults is worth confirming rather than inheriting.

---

## Tomorrow — cutover day

**Morning, before staff arrive:**
- Re-run the acceptance checks from step 4. Overnight edits happen.
- Confirm the trigger flow is ON and the fallback copy is still OFF.
- Confirm the viewer opens clean from a normal staff account, not just yours.

**At cutover:**
- Announce: edits happen in SharePoint; FRM10-12 is now a mirror and won't save changes.
- Watch the first hour of trigger-flow runs. Manual edits are the first real test of 2c.
- Watch the request budget through the first day. Real staff editing consumes it too.

---

## Abort criteria — decide against these, not in the moment

Re-evaluate the hard cutover if **any** of these is true at the end of build night:

1. The full transfer run does not complete every row (throttling, or Gate 0's cap confirmed
   tight with no uplift available).
2. The reconciliation pass isn't built and tested — a cutover without it strands `Active` rows
   for finished units with no Excel side left to fix them from.
3. Viewer parity fails: missing columns, wrong order, or a row-count gap that can't be explained.
4. Monday.com is not receiving production data **and** the 2a fallback isn't re-enabled — that
   combination means nothing tracks stage progression from tomorrow.

**Fallback if aborted**: everything in steps 1–3 is still net progress and none of it breaks the
current setup. Staff keep editing FRM10-12, re-enable the stage-stamping copy, and the final
sync becomes a dress rehearsal to re-run. Nothing here is one-way.

---

## Working in parallel tonight

Practical constraint worth knowing before splitting up: **browser automation is scoped to one
tab group per Claude session**, and the Power Automate designer is a stateful single-document
editor. Two agents in the same flow will overwrite each other — the 2026-08-18 incident where a
dropdown reselection wiped every field mapping is the flavour of damage available here.

**What actually works** — separate Claude Code terminals, split by non-overlapping surface:

| Session | Surface | Touches |
|---|---|---|
| A | Power Automate | Steps 2a–2e. **The only session that triggers flow runs.** |
| B | SharePoint UI | Step 1 schema, then step 3 views. No flows. |
| C | Repo, no browser | Step 5's ColumnMap edit, Sync-PowerQuery, doc updates |

Rules: never two sessions in the same flow's designer; session A owns the request budget; B
waits for A's confirmation that step 1's columns exist before mapping anything against them.

Sessions can coordinate directly — `ListAgents` shows other local Claude sessions on this
machine, and `SendMessage` reaches them.
