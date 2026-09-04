# Pioneer Transformer — build night 2026-09-01, presentation 09:00

> ## 🛑 THIS HEADER WAS WRONG. Corrected 2026-09-03 by 🟠 D — read this first
>
> **The block below claims `A6` never ran and the sales app was never edited. Both are false,
> and both were false for two days.** Verified live against the tenant on 2026-09-03 22:30 by
> REST (read-only GETs), by 🟢 B:
>
> | | Sep 1 export (what the block below assumes) | **Live 2026-09-03** |
> |---|---|---|
> | Items | 1038 | **1052** |
> | `Planned Tanking Date` populated | 0 | **913** |
> | `Planned Delivery Date` populated | 0 | **335** |
> | `Location` populated | 175 | **211** |
> | `Technical Notes` / `Info+` | 0 | **0** |
>
> **`A6` DID run.** `Technical Notes` and `Info+` still at zero is the signature of a run made
> with **A5 mapped at 2 of 7** — exactly the state the flow was left in. Nobody recorded it
> because the session that would have was killed mid-sentence by a spend limit.
>
> **The sales app WAS edited and is live.** Its fan-out creates `Order Items` rows in production
> right now — `P10003-1/2`, `P10003-2/2` (2026-09-03 15:00), `P00005-1/1` (13:21),
> `22157-8/10`…`10/10` (Sep 2) were all created by real users, not by a flow.
>
> **So `Order Items` has TWO WRITERS that do not know about each other** — the app's fan-out and
> the transfer flow. Anything below that assumes a single writer, or an untouched list, is
> planning text and not a description of the system.
>
> **What the block below still gets right:** the cutover as a whole did not complete, **D5 was
> cut so the viewer is genuinely NOT deployed**, the live FRM10-12 is untouched, and staff are
> unaffected. This is a **parallel run** — staff still fill in FRM10-12 while the app also
> creates Order Items.
>
> **Do not undo anything on the strength of the text below.** In particular, never "fix" a blank
> `Tanking Date` by reverting the 2026-09-01 re-source: the Planned columns are populated now,
> so a refresh is the fix. Current state lives in `../../BUILD-NIGHT-2026-09-03.md` (KEY FACTS),
> which supersedes this header.
>
> ---
>
> ## ⚠️ ORIGINAL HEADER — SUPERSEDED, kept for the record
>
> **The cutover did NOT happen. `A6` never ran.** ← **FALSE, see above.** Both build sessions
> were cut off by a Claude usage limit at **~02:31** and came back after the 05:30 hard stop.
> This runbook is the plan as written; it is **not** a record of what was executed.
>
> **Nothing is broken and nothing needs undoing.** No flow ran, so `Order Items` holds exactly
> what it held before the night started — nothing written, nothing fabricated. ← **FALSE, see
> above: the flow ran and wrote 913/335/211.** The live
> FRM10-12 is untouched, the viewer was never deployed, the sales app was never edited ←
> **FALSE, the app is live and creating rows**, and the
> trigger flow is still ON in its normal state. Staff are unaffected.
>
> ### Landed and safe to keep
> - **B1** — all 7 new columns live on `Order Items` (~~empty; the run that fills them never
>   ran~~ — **not empty: 913 / 335 / 211 populated, see above**)
> - **B2** — `Production Floor` and `Planning` views live and working on the real 1,038 rows
>   (**now 1052 rows, and there are SEVEN views, not two — see the views note below**)
> - **D2 / D3** — ColumnMap remapped and synced into the viewer workbook, committed
> - **D0** — the `int()` failure root cause (case-sensitive `EC` guard); scanner in scratchpad
> - **D5b** — refresh owners named
> - **E** — staff guides EN + FR, visual companion, demo cheat sheet
> - **A0** — quota ruled out as the cause of the old failures
> - **A5b (`UpdateOrderItem` only)** — the 4 fabricating Tanking/Delivery mappings removed
>
> ### Not done
> - **A5b on `CreateOrderItem`** — still carries all 4 bad mappings
> - **A5c** — `toLower()` fix not applied
> - **A5, A6, A7, A8** — no transfer run, no reconciliation
> - **C2 / C3** — fan-out formula written but never opened in Studio
> - **B3 / B4** — site home page unfinished, permissions unchecked
> - **D4 / D5** — viewer not verified, not deployed
>
> ### ☠️ The one live landmine
> **Do not refresh the viewer workbook until after a successful `A6`.** D2 repointed
> `Tanking Date` / `Delivery Date` at `Planned Tanking Date` / `Planned Delivery Date`, which
> exist but are empty. A refresh now blanks both columns on every row. This is expected, not a
> bug, and must not be "fixed" by reverting the re-source.
>
> ### Correct resume order
> 1. Re-confirm the 4 Tanking/Delivery keys are gone from `UpdateOrderItem` (saved, JSON not
>    re-read — the designer froze)
> 2. Strip the same 4 from `CreateOrderItem`
> 3. `A5c` `toLower()`, both actions, six stages
> 4. `A5` — map the 7 columns. `Planned Delivery Date`'s internal name is truncated at 32
>    chars (`Planned_x0020_Delivery_x0020_Dat`); use the dynamic-content picker
> 5. Re-scan a fresh snapshot, then `A6`, then refresh the viewer, then `D4`/`D5`
>
> Full detail in `Clients/Pioneer Transformer/BUILD-NIGHT-STATUS.md`.

## Context

Staff move off editing FRM10-12 and onto SharePoint. You present at 09:00, must be on site
at 08:00, leave ~06:30. **Working window is 00:30 → 05:30, with 05:30–06:30 reserved for
freeze, final checks and getting out the door.** Five hours, not a night.

Target is the hard cutover, sequenced so a good demo is locked in early. Everything visible
lands first; everything invisible lands after. If the night goes badly at 04:00 you still walk
into the room with a working system.

### Decisions taken (2026-09-01, don't re-litigate)

| | Decision |
|---|---|
| Fan-out | Inline Power Fx on the sales app's Save button |
| SA rows | Driven off `Order.SA` |
| Reconciliation | Build the flow tonight |
| Presentation | Full visual companion, plus staff-facing docs |
| Staff docs | How-to for the lists and view tabs, "come ask me" for help |
| Site | Quick Launch links + a home page |
| Viewer deploy | Overwrite in place at the Index path — keeps FRM09 and BO Manager working |
| Viewer refresh | Daily, manual, named owner, documented |
| Planned dates | Create both columns, re-source the viewer, keep 76 columns; cleanup deferred |

### What changed since the first runbook

Four findings from tonight's audit that the earlier `cutover-plan-2026-09-02.md` got wrong or
missed. These drive the plan below.

1. **Hand-typed `item()?['Protector & Switchgear Item #']` silently writes blanks.**
   `order-items-power-automate-flows.md:872-879`: any display name containing `#` arrives from
   the Excel connector XML-encoded (`PO Item #` → `PO Item _x0023_`), and the plain name
   *"will silently return nothing instead of erroring."* Use the dynamic-content picker.
   `Info+` contains `+`, whose encoding has never been tested here — verify before mapping.
2. **FRM09 and BO Manager will silently freeze.** Both resolve FRM10-12 through a single row
   in the live SharePoint `Index` list (`Index.csv:10` →
   `/sites/PioneerPlanificatio/Shared%20Documents/General/FAB/Revue/FRM10-12.xlsx`). Verified
   against FRM09's actual embedded M: `ImportFromIndex("FRM10-12", "TableOrders")`. They keep
   refreshing *without error* against a file that stops changing. Not mentioned anywhere in the
   old runbook. **Fix: deploy the viewer in place at that exact path** (Track D).
3. **The viewer's formulas and conditional formatting are genuinely intact** — verified at the
   XML level in `viewer/workbook/FRM10-12.xlsx`, not taken from a comment. `Price`,
   `Estimated Delivery Date`, `Price CAD/USD`, `Navigation Order/Model` all carry live
   structured-reference formulas. One less thing to worry about.
4. **Only 7 of 76 viewer columns are blank, and 5 are the ones you're building.** After tonight
   just `Duplicate` (never migrated) and `Duplicate Order` (frozen pending review) remain. Both
   explainable in a sentence.

5. **The planned/actual date split is unbuilt on both sides.** `Planned Tanking Date` and
   `Planned Delivery Date` don't exist on `Order Items` (confirmed 2026-09-01), and the viewer
   still sources `Tanking Date`/`Delivery Date` from the `{Stage} End Date` fields
   (`ColumnMap.pq:162,165`). Those End Date fields currently hold values the original backfill
   copied there by mistake — which is the only reason the viewer looks right today. Tonight:
   create the two columns (B1), map them (A5), re-source the viewer (D2). Cleanup of the old
   fabricated values is **deliberately deferred**.

### Two hazards to name before anyone starts

- **The transfer flow must never run after the viewer is deployed in place.** Its Excel source
  becomes the viewer, whose `TableOrders` is generated *from* Order Items. Turn it off the
  moment the final sync completes.
- **Reconciliation is being decoupled from the transfer run.** The original spec tracked
  processed Unit IDs in a run-time array variable, which forces it to live inside the transfer
  flow. Build it instead as a **standalone scheduled flow** that diffs `Order Items` rows at
  `Item Status = Active` against a fresh `TableOrders` + Archive pull. Same result, no
  coupling, and it can be built and tested while the transfer run is executing.

---

## Tiers and the hard stop

**Tier 1 — demo-safe. Target 03:30.** Below this line the 09:00 presentation works.

- 5 columns created and populated
- Views built (Production Floor, Planning)
- Site home page + Quick Launch
- Fan-out live in the sales app
- Viewer refreshed at full column parity

**Tier 2 — hard cutover. 03:30 → 05:15.**

- Reconciliation flow built and run
- Trigger-flow hygiene complete (fallback parked, stamping stripped)
- Viewer deployed in place, read-only enforced, Index row verified
- Transfer flow disabled

**05:30 is a hard stop.** No new work after it, verification only. Mistakes made at 05:00 on no
sleep are how a demo dies. If Tier 2 isn't done by 05:15, stop and present Tier 1 — say the
cutover completes this week, which is a perfectly good outcome in the room.

---

## Timeline

**Revised 01:30 — planning ran an hour long, so this is a 4-hour window, not 5.** The slack is
gone, not the work. See the note under the table for what that costs.

| Time | A — Power Automate | B — SharePoint UI | C — Power Apps (you) | D — Repo | E — Docs |
|---|---|---|---|---|---|
| 01:30 | Gate 0: quota | **B1: 7 columns** | Verify `Order.SA` | **D0 int() pre-scan** | Start guide |
| 02:00 | A2, A3 | B2 views | Fan-out build | D1 dirty state, D2 ColumnMap | Guide + companion |
| 02:30 | A4, A5, **A5b** | B3 home page + nav | Fan-out test | D3 sync | Cheat sheet |
| 03:15 | **Run final sync** | B4 permissions | Buffer | D3/D4 refresh + parity | — |
| 03:45 | **A6b: fix the ~8 rows** | Verify views | — | — | — |
| 04:15 | A7 reconciliation build | **← Tier 1 done →** | — | — | — |
| 05:00 | Run A7 | — | — | D5 deploy in place | — |
| 05:20 | **Disable transfer flow** | — | — | D5b, D6 commits | — |
| 05:30 | **HARD STOP — verify only** | | | | |

D0 is the only addition to the critical path, and it pays for itself — it converts A6b from a
run-history crawl into working from a list you already have.

**What the lost hour costs, stated up front rather than discovered at 05:00**: A7, the
reconciliation flow, is a 60–90 minute build that now starts at 04:15 and has to also *run*
before 05:20. It is the item most likely not to fit. If it's clearly not going to land by 05:00,
switch to the offline route — `Archive active.xlsx` is in the repo and `Order Items` exports to
CSV, so the stale set can be computed locally and fixed via Quick Edit in a fraction of the
time. That gets the data correct for the demo and leaves the flow itself for the next session.
Everything else in Tier 1 still fits.

**The one blocking dependency**: B's Step 1 gates A's 2d and D's ColumnMap. Everything else runs
free. B goes first and announces when the columns exist.

---

## Track A — Power Automate

**Owns the request quota. The only track that triggers flow runs.** Nobody else runs anything
in Power Automate tonight.

### A0. Gate 0 — quota (15 min, before touching anything)

Last bulk attempt ran ~350 of ~1000. Hypothesis: a Power Platform *request* cap, not a defect —
the platform meters actions, the trigger flow does ~17/row, 350 × 17 ≈ 5,950, and seeded O365
licences commonly cap near 6,000/24h.

- Power Platform admin center → Analytics → Power Automate → requests/throttling
- The failed batch's run history: look for **429** / `ActionThrottled` vs runs that never fired
- Confirm the flow owner's actual licence

**If the cap is confirmed tight**: the run must fit the remaining budget. A2/A3 below cut per-row
cost roughly in half, which may be the difference. Report the number to the other tracks —
it decides whether the full run is safe in one pass.

### A1. Pre-flight (10 min)

- [ ] Transfer flow pagination threshold is **5000**, not the `10` left from testing
- [ ] **Re-verify the transfer flow's Excel file-picker still points at the live FRM10-12** —
      recorded as "not yet confirmed" since 2026-08-17 and never re-checked
- [ ] Nobody has FRM10-12 open in Excel Online (co-authoring during refresh is what corrupted
      the table binding on 2026-08-28)

### A2. Park the fallback (5 min)

**Save As** on `Order Items - created or updated trigger` →
`Order Items - stage stamping (FALLBACK, do not enable)`. Save As produces a disabled copy —
confirm it is off, leave it off. This is your insurance if Monday.com doesn't work out.

### A3. Strip stage stamping from the live trigger flow (20 min)

Remove the 16 `{Stage} Start/End Date` stamps, the `N/A` handling, and the advance-to-Pending
chain. This is the bulk of the per-row action cost behind Gate 0's ceiling.

### A4. Fold TextField sync into the transfer flow (30 min)

Move the Lookup → TextField companion writes into `CreateOrderItem`/`UpdateOrderItem`. The flow
already resolves `ClientIdToWrite`/`ModelIdToWrite`/`ModelRevisionIdToWrite`, so writing the
companion in the same action costs **zero extra requests**.

**Do this before the run.** Real TextField staleness was found on 2026-08-31, and the Production
Floor view displays `Order_Number_TextField` — stale values are visible in the demo.

Keep the trigger flow itself alive: it still serves manual edits staff make from tomorrow on.

### A5. Map the 7 new columns (40 min) — *blocked on B1*

Add to both `CreateOrderItem` and `UpdateOrderItem`:

> **⚠️ This table is wrong in three places, and `transfer-flow-forensics-2026-09-04.md` §6
> supersedes it.** Corrected 2026-09-04 by 🟠 D from 🔵 A's verified capture — source keys read
> from a real `List rows present in a table` output, target internals read from
> `_api/web/lists/getbytitle('Order Items')/fields`. **Nothing retyped from a display name.**
> Use §6's expressions verbatim; the three errors are called out inline below.

| Column | How |
|---|---|
| `Technical Notes` | ~~Plain — no special characters~~ **← WRONG.** All 7 non-blank values are **raw SharePoint HTML** that already round-tripped out of SharePoint once. Target is a `Note` field. Flagged, not fixed — stripping the HTML is a data decision, not a mapping one |
| `Configuration` | ~~Plain~~ **← WRONG, it needs a guard.** 9 of its 510 non-blank values are Excel **time** cells that render `00:00:00`. See §6 for the guard expression |
| `Section Qty` | `int()`/`float()` **with a blank + non-numeric guard** — check for `EC`, `AT`, `RE`, `BO`, `TE`, `B1`–`B3` first. An unguarded `int()` is exactly what failed at iteration 114 on the stage dates. *(Verified genuinely clean — 119/119 parse — but keep the guard.)* |
| `Protector & Switchgear Item #` | **Dynamic-content picker only.** Never hand-type. Key escapes the `#` but **not** the `&`: `Protector & Switchgear Item _x0023_`. No collision with `Protector & Switchgear PO` (`ProtectorSwitchgearPO`) |
| `Info+` | ~~**Inspect a test-run JSON first**~~ **← no longer needed, it was done.** The key needs **no escaping** — it is literally `Info+` |
| `Planned Tanking Date` | Raw `TableOrders[Tanking Date]`, same serial→date conversion as everywhere else |
| `Planned Delivery Date` | Raw `TableOrders[Delivery Date]`, same conversion |
| `BO` | *(added)* Passes through **exactly as stored**. Per the user it is derived-by-default but **manually overridable, and 7 units deliberately differ from the derived value.** Do **not** compute it and do **not** add a derive-and-compare guard — either silently reverts those 7 |

Spot-check the four text columns in raw `TableOrders` for `indéterrminé` / `CONFRIMED` / `EC`
before trusting them.

> **Expected counts, to verify a run against rather than eyeball** (from
> `FRM10-12_2026-09-01_13h43m.xlsx`, 1039 rows): `Info+` 97 · `Technical Notes` 7 ·
> `Protector & Switchgear Item #` **0** · `Configuration` 510 (501 after the guard) ·
> `Section Qty` 119 · `BO` 626.
>
> **`Protector & Switchgear Item #` is 100% blank at source.** A6's acceptance test "the 5 new
> columns are populated, not blank" is **impossible** for that one and will look like a failure
> when it is the correct result. Verify it by confirming the mapping exists — **never by
> counting.**

### A5b. Verify the Tanking/Delivery exception is actually built — **do this before the run**

The 2026-08-21 correction says raw `Tanking Date`/`Delivery Date` must go to the **Planned**
columns, and that `Tanking End Date`/`Tanking Status` and `Delivery End Date`/`Delivery Status`
are **left blank at backfill — not set from this column at all**.

It was documented. Whether it was ever *built* is unverified, and the Planned columns didn't
exist until tonight, so it cannot have been fully wired.

**Open both actions and confirm, on each of `CreateOrderItem` and `UpdateOrderItem`:**
- `Tanking End Date`, `Tanking Status`, `Delivery End Date`, `Delivery Status` are **not
  mapped at all**. If any of them still derives from the raw date column, remove it
- The other six stages (Coiling, Stacking, Assembly, Drying, Testing, Finishing) keep their
  existing End Date/Status mappings — only Tanking and Delivery are exceptions

**Why this is a run-blocker**: if those mappings are still live, tonight's full run writes a
fabricated `Completed` status and a fake completion date onto ~1000 rows. That turns a deferred
cleanup of a handful of historical rows into a deferred cleanup of the entire list — and it
happens on the one run that can't be undone by re-running, because the flow gets disabled
afterwards.

### A6. The final sync (30–45 min)

1. Confirm nobody has FRM10-12 open; snapshot into `live-workbook-data/`
2. Refresh FRM10-12 via the **Office Script button** — never Refresh All / COM `RefreshAll`
3. **Get D0's landmine list** — the Unit IDs and columns that will fail the `int()` conversion.
   Re-scan the post-refresh snapshot to confirm the list is still accurate
4. **Turn OFF `Order Items - created or updated trigger`** for the duration. A4 means the
   transfer flow writes TextFields itself, so the trigger flow would only burn ~1000 redundant
   runs against the quota
5. Run the transfer flow, full table
6. Turn the trigger flow back on

**Acceptance**: row count reconciles against `TableOrders` (~980) and the 1038 in the list; the
5 new columns are populated not blank; TextFields current on a sample; no 429s; the failed
iterations match D0's predicted list and nothing else.

### A5c. Fix the `EC` guard — 10 min, and it removes A6b entirely

**D0 found the root cause: three of the nine `EC` markers are lowercase `ec`, and
`equals()` is case-sensitive.** Wrap both sides of the comparison in `toLower()` on all six
mapped stages, both actions — the exact expressions are in D0's results below.

Do this **before** the run. It is a 10-minute edit that converts A6b from 30 minutes of manual
cell-fixing into nothing, and it makes the one irreversible run land clean.

### A6b. Fix the failing rows (20–30 min) — only if A5c was skipped

**Roughly 7–8 of ~1000 rows will fail**, always on a single column, always an `int()` conversion
inside `Update item`. The loop keeps going and the rows still land — only that one column is
left unwritten. This is known behaviour, not a sign the run went wrong.

> **⚠️ BOTH PARAGRAPHS BELOW ARE NOW WRONG. Corrected 2026-09-04 by 🟠 D, flagged by 🔵 A.**
> They rest on one assumption — that Sep 1 was the last run ever and FRM10-12 was about to go
> read-only. **A8 never ran and D5 was cut**, so the flow is not disabled and the workbook is not
> read-only. We are in a **parallel run**, and both instructions invert:
>
> - **"This is the last transfer run that will ever happen"** — it wasn't. The flow can and will
>   run again.
> - **"Fix in SharePoint, not in Excel"** — **backwards now.** FRM10-12 is still the live source
>   staff type into. A SharePoint-side hand-fix gets **overwritten by the next run**, because the
>   run reads Excel and writes SharePoint. Under a parallel run, **fix it in Excel**, where staff
>   work and where the next run will read it from.
>
> This flips back the day the cutover actually completes. Until then, treat the original text
> below as describing the intended end state, not today.

~~**This is the last transfer run that will ever happen**~~ — the flow gets disabled at A8, and
FRM10-12 becomes read-only. So whatever value ends up in those cells tonight is what SharePoint
holds permanently. Worth fixing properly rather than leaving null.

~~**Fix in SharePoint, not in Excel.**~~ The source workbook is about to become a read-only
mirror, so correcting it there buys nothing and would need a second run to propagate.

Procedure:
1. Cross-check the failed iterations against D0's list. If they match, no run-history crawl is
   needed at all — you already know the Unit ID and column for each
2. For anything D0 didn't predict, open the run, read the error and the iteration's `Unit ID`
3. Decide the right value per marker, don't just blank it:
   - `EC` ("En cours") in a stage date → the date is genuinely unknown; leave the date empty and
     make sure that stage's `Status` reads `In Progress`
   - Any other non-numeric marker → check what it means before writing. `AT`, `RE`, `BO`, `TE`,
     `B1`–`B3` are all known composite-`Status` prefixes in this data
4. Edit the cells directly in the `Order Items` list

**Optional hardening if A is ahead of schedule** (~15 min): add the same `EC`-style guard the 8
production-stage columns already carry to `Tank Delivery Date`, `Original Tanking Date` and
`Manual Estimated Delivery Date`, on both `CreateOrderItem` and `UpdateOrderItem`. It won't
change tonight's outcome — you'd still fix the same cells by hand — but it means a mid-run
failure can't cascade if the data has drifted further than D0's scan found.

### A7. Reconciliation flow (60–90 min, Tier 2)

Build **standalone**, not inside the transfer flow (see hazard note above):

1. `Get items` on `Order Items` where `Item Status = Active`, pagination on
2. `List rows present in a table` on `TableOrders` — the current live set
3. Filter to Active Unit IDs with no matching `TableOrders` row — **this is the stale set, and
   nobody has ever counted it. Record the number, it's a real finding either way**
4. For each, resolve the Archive workbook via the `Index` list (same as `ImportFromIndex.pq`)
   and finalize `Cancelled` (Location `AN`) or `Delivered` (Location `LI` + real Delivery Date)
5. Anything unresolved → flag, don't guess

Then run it. **Check whether it's genuinely unbuilt before building** — the last two "not yet
built" items in that doc both turned out to already exist.

### A8. Disable the transfer flow (5 min, after D deploys the viewer)

Non-negotiable. Once the viewer sits at the FRM10-12 path, the transfer flow's source is
generated from its own destination.

---

## Track B — SharePoint UI

No flows, no quota. Nothing here can break data. **Start immediately — B1 gates two other tracks.**

### B1. The 7 columns (25 min) — *do this first, announce when done*

On `Order Items` (PnP PowerShell is still blocked on this tenant — but **site-context REST is
not**, corrected 2026-09-03: it did 19 field creates + 73 item updates, all 2xx. Test a GET on
`_api/web/lists/getbytitle('Order Items')/fields` before doing this by hand):

| Column | Type | Why |
|---|---|---|
| `Technical Notes` | Multiple lines of text | Viewer parity |
| `Info+` | Single line of text | Viewer parity |
| `Protector & Switchgear Item #` | Single line of text | Viewer parity |
| `Configuration` | Single line of text | Viewer parity |
| `Section Qty` | Number | Viewer parity |
| `Planned Tanking Date` | Date and Time → **Date Only** | Planned/actual split |
| `Planned Delivery Date` | Date and Time → **Date Only** | Planned/actual split |

Types must match `ColumnMap.pq`'s codes exactly. **Confirmed 2026-09-01: none of these seven
exist yet**, including the two Planned columns the 2026-08-21 correction assumed would be
created.

Power Query reads these by **display name** — `SharePoint.Tables` does, confirmed by
`"Protector & Switchgear PO"` and `"JS #"` already working as `SourceField` values. The
encoding problem is Power Automate's alone.

**Tell A and D the moment these exist.**

### B2. Views (45 min)

**`Order Items` → `Production Floor`** — spec in `order-items-manual-build-checklist.md:223-253`:
- Columns: `Unit ID`, `Order_Number_TextField`, `Location`, `Item Status`, `Coil Winder`,
  `Manual Estimated Delivery Date`
- Filter `Item Status = Active`; **Group by `Location`**; sort by `Manual Estimated Delivery
  Date` ascending
- Format this column → **Choice column colors** on `Location` — this does most of the visual
  work for free. Try a **Gallery** view for a card layout

**`Order Items` → `Planning`** — mirror `TableOrdersColumnOrder.pq`'s order so the list reads
like the workbook staff already know.

Verify both *after* A6's run, not before — they depend on TextField accuracy.

> ### ⚠️ There are SEVEN views live on `Order Items`, not two. Added 2026-09-03 by 🟠 D,
> ### corrected 2026-09-04 from the live definitions.
> This section plans `Production Floor` and `Planning`. Read from the live view definitions:
>
> | View | Cols | Filter / shape |
> |---|---|---|
> | `All Items` **[default]** | 74 | no filter |
> | `Production Floor` | 6 | Active · grouped by `Location` · sorted Manual Est. Delivery Date |
> | `Planning` | 24 | Active · sorted Planned Delivery Date |
> | `Angelique reunion du lundi` | 24 | Active · sorted Planned Delivery Date |
> | `Angelique bobinage` | 9 | **no filter — see below** |
> | `JF - Test` | 6 | SA Job = No · grouped by Model |
> | `BO Tracking` | 23 | BO not null · grouped by `BO` · sorted Planned Tanking Date |
>
> Plus `Direction - Prix (demo)` (11 cols, sorted Order Date desc) on the **`Order`** list.
>
> **`Overview` does not exist.** An earlier version of this note said it did, on the strength of
> one line in a Sep 1 transcript. It was renamed or deleted since, and SharePoint does not retain
> deleted view definitions, so it is unrecoverable. `Planning` is the outline-level-1 view that
> line was describing. **Do not go looking for it, and do not document it.**
>
> Three consequences worth having in writing:
> - Both staff guides tell staff to open `Production Floor` and mention no others. The bilingual
>   `views-guide-sharepoint*.md` pair covers all four staff-facing views.
> - **`Angelique reunion du lundi` is an EXACT copy of `Planning`, never customised.** Verified
>   programmatically: 24 fields each, same order, zero fields in either that aren't in the other;
>   the CAML differs only in element order (`Where` before `OrderBy`), which is the same query.
>   Someone used "Save view as" and stopped there. It is the worked example in the views guide,
>   worded as "a colleague has already made their own copy" — **not** as "made a copy and tweaked
>   it", which would be a checkable false claim.
>   *Worth a Friday question, not a doc note:* an uncustomised copy may mean she saved it meaning
>   to change it and never got there. That's a "does she need a hand" conversation.
> - **`Angelique bobinage` has NO filter at all** — no `ItemStatus = Active`, so it shows
>   Delivered and Cancelled units alongside live ones. Nine columns, winding-focused. **It is the
>   only staff-facing view without the Active filter.** May well be deliberate; recorded so the
>   next person doesn't rediscover it as a bug.
> - **`JF - Test` is a personal experiment that landed as a PUBLIC view.** Nobody's fault — new
>   views default to public. It is deliberately **not named in the staff guide**: it is the
>   reason the personal-vs-public section exists, but naming a colleague's stray view in a doc
>   the whole floor reads makes people afraid to touch anything.
>
> The `NumberOfLines=6` Note-column problem (KEY FACTS) was fixed on **Planning**. Any view
> carrying a Note column has the same ~315px-row bug; `BO Tracking` (23 cols) is worth a look.
>
> ### ☠️ `BO Tracking`'s `Collapse="TRUE"` is LOAD-BEARING. Added 2026-09-04.
> Its `GroupBy` carries **no `Ascending` attribute**, so it defaults to ascending, which puts
> **blank values first** — and the blank `BO` group is **979 rows**. Collapsed, that is harmless:
> every group shows its header and count. **Un-collapse it and the view breaks instantly** — the
> blank group eats the whole row budget and every other group falls off the end with no
> next-page link. It looks exactly like data loss.
>
> This is not theoretical: **it bit the user on `BO Tracking` on 2026-09-04 and cost real time.**
>
> **`Production Floor` grouped by `Location` has the identical shape — 827 units with no
> Location.** Any view grouping on a column where one value dominates is one setting away from
> the same failure. The two settings that prevent it: groups **Collapsed**, and Item Limit set to
> **"Display items in batches"** rather than **"Limit the total number of items returned"**.
>
> Third trap, worth knowing before anyone tries to "fix" the order: **`GroupBy` overrides the
> `OrderBy`/Sort section for the grouped column.** Setting a sort direction there has no effect —
> the direction comes from the `GroupBy` section alone. So the obvious fix silently does nothing.
>
> Staff-facing version of all of this is `views-guide-sharepoint*.md` section 7.
>
> ### ⚠️ Column formatting is FIELD-level, not view-level. Added 2026-09-04.
> There is **no per-view column formatting** in SharePoint. Whatever formatter lands on a field
> appears in **every view that shows that field.** So a formatter on `Planned Tanking Date` shows
> up in `Planning` and `Angelique reunion du lundi` too, not just the view it was built for —
> and three of the seven views carry that field.
>
> Consequence worth stating because it is counter-intuitive: **you cannot scope a formatting
> experiment to one view.** A change made while looking at `BO Tracking` is a change to every
> view carrying that column, including the two nobody was looking at.
>
> Live formatter state, verified by REST on 2026-09-04 (not assumed): `BO` carries the
> orange/green fills · 15 part columns carry the strikethrough · the three `OK` columns are
> **deliberately plain** · **`Planned Tanking Date` has NO formatter.** That matches BO Manager's
> three real CF rules exactly.
>
> **Date-urgency formatting on `Planned Tanking Date` is DEFERRED, and one route is dangerous** —
> hand-written formatting using `@now` **freezes** this view (reproduced A/B/A/B), and a
> calculated column is not the workaround because SharePoint evaluates `TODAY()` at **write**
> time, so an urgency flag is right the day it is made and **silently wrong** after. Full
> writeup, untried routes and the matching hex values: `roadmap.md`, deferred-items section.
>
> ### New: `Bo Sort Date` — the first calculated column on `Order Items`. Added 2026-09-04.
> Added by the user. A calculated column that substitutes a **`2999-12-31` sentinel** for a blank
> `Planned Tanking Date`, so a sort puts unplanned units **last** instead of first (a blank date
> sorts as the *earliest* date, which is the trap above). Verified by 🟢 B: **139 blank rows, all
> carrying the sentinel, no variants.**
>
> ⚠️ **It is a calculated column, so it is the first thing on this list that is NOT writable.**
> Anything that enumerates and writes `Order Items` fields — the transfer flow's `CreateOrderItem`
> / `UpdateOrderItem`, any REST `MERGE` built from a field list — must **exclude** it. A write
> attempt against a calculated field fails, and per KEY FACTS a failing action in that flow
> reports up as `Failed` while other rows still land, so it would be diagnosed as something else.

### B3. Site home page + Quick Launch (45 min)

The thing staff actually land on. High demo value, zero risk.

**Quick Launch (left nav)**: direct links to `Order Items` → Production Floor, `Order Items` →
Planning, `Order`, `Models`, and the viewer workbook. Remove or demote anything staff don't need.

**Home page** (SharePoint page editor):
- Short "what changed" intro — you now work here, not in Excel
- Tiles/links to the key views, with one line each on what the view is for
- Embed or link the how-to guide from Track E
- **"Questions? Come ask [you]."** — explicit, by name, prominent

### B4. Permissions sanity check (10 min)

No permission restriction is documented anywhere, and staff already edit the sibling
`Order`/`Models` lists, so this is likely a non-issue. Confirm rather than assume: open
`Order Items` as a normal staff account and edit a cell.

---

## Track C — Power Apps (you)

Your app, your call. The demo centrepiece.

### C1. Verify `Order.SA` before writing any logic (10 min)

Confirmed from the schema export: `Type="Boolean"`, internal name `SA`, group "Pioneer Order
Columns". A clean Yes/No.

**The open question is grain, and live data answers it**: for an order with `Qty = 5` and
`SA = true`, does that mean **five** SA rows (`21865-1/5 SA` … `21865-5/5 SA`) or **one**?
Filter `Order Items` on `SA Job = Yes` and look at their `Qty` values. The Unit ID format pairs
an SA row to a specific unit, which points at per-unit — but confirm it, don't assume.

### C2. Fan-out on Save (60 min)

After the Patch that creates the Order, with `newOrder` as its result:

```
ForAll(
    Sequence(newOrder.Qty),
    Patch('Order Items', Defaults('Order Items'),
        {
            Title:            newOrder.'Order Number' & "-" & Value & "/" & newOrder.Qty,
            'Order Number':   newOrder,
            'Unit #':         Value,
            Qty:              newOrder.Qty,
            'SA Job':         false,
            'Item Status':    {Value: "Active"},
            Client:           newOrder.Client,
            Model:            newOrder.Model,
            'Model Revision': newOrder.'Model Revision'
        }
    )
)
```

Then, if `newOrder.SA` and C1 says per-unit, a second `ForAll` writing `Title` with the
` SA` suffix and `'SA Job': true`.

**Main units need no SA/Models disambiguation at all** — Client/Model/Model Revision copy
straight off the Order record the app just created. Only SA rows need the
`ParentModelId eq <id> and SAModel eq 1` resolution, and if that proves fiddly in Power Fx,
create the SA row with the parent's Model and let the existing flow correct it.

**Guards:**
- Only fan out on **create**, never on edit — otherwise editing an order duplicates every unit
- Idempotency: `LookUp('Order Items', Title = <id>)` before patching, so a double-tap on Save
  can't double-create
- Qty changes after the fact are **out of scope tonight** — no mechanism exists for this today
  either (`Regrouped Into` is manual and unbuilt), so it's not a regression

### C3. Test (20 min)

Create a throwaway order with `Qty = 3`, confirm 3 rows with correct Unit IDs, then one with
`SA = true`. **Delete the test rows before the demo.** Note the Unit IDs you create so nothing
is missed.

**Rollback**: Power Apps keeps version history. If Save misbehaves at any point, restore the
previous version immediately — sales creating orders tomorrow matters more than fan-out.

---

## Track D — Repo (no browser)

### D0. Pre-scan for `int()` landmines (20 min) — **must finish before A6's run**

Roughly 7–8 rows will fail the run on an `int()` conversion. Find them now instead of hunting
them through 1,000 iterations of run history afterwards.

Scan `live-workbook-data/FRM10-12_2026-08-31_09h41m.xlsx` (and re-scan the fresh snapshot A6
takes) for **non-blank, non-numeric** values in every `TableOrders` column that feeds an `int()`:

- The 8 production-stage `{Stage} Date` columns — already guarded for `EC`, so anything *other*
  than `EC` here is a new marker worth knowing about
- **`Tank Delivery Date`, `Original Tanking Date`, `Manual Estimated Delivery Date`** — the
  likeliest culprits. `order-items-power-automate-flows.md` marked these "no composite-status-code
  guard needed, confirmed clean 2026-08-18", but that was a count of non-blank values, not a check
  for non-numeric ones. Data has drifted since
- `Section Qty` — new tonight, unscanned, and A5 guards it precisely because of this class of bug
- `Time (days)`, and anything else numeric in `TableOrdersColumnOrder.pq`

Read-only — don't edit the workbook.

### D0 — DONE 01:45. Results.

Scanned `FRM10-12_2026-08-31_09h41m.xlsx` (`TableOrders` = `B5:CE985`, 82 columns, 980 data
rows) by parsing the sheet XML directly. Method: in a numeric column, any cell carrying a
shared-string or inline-string type is by definition non-numeric.

**9 landmines. All in `Coiling Date`. All the `EC` marker. Every other int()-bound column is
clean.**

| Row | Unit ID | Column | Value |
|---|---|---|---|
| 246 | `21972-1/1` | Coiling Date | `EC` |
| 270 | `21387-4/6` | Coiling Date | `EC` |
| 284 | `21830-1/5` | Coiling Date | `EC` |
| 298 | `21795-1/5` | Coiling Date | **`ec`** |
| 334 | `21992-1/6` | Coiling Date | `EC` |
| 372 | `21994-2/3` | Coiling Date | `EC` |
| 414 | `21842-4/5` | Coiling Date | `EC` |
| 429 | `21843-1/1` | Coiling Date | **`ec`** |
| 440 | `21957-7/9` | Coiling Date | **`ec`** |

### The actual root cause — case sensitivity

**Three of the nine are lowercase `ec`.** The built guard is
`equals(trim(item()?['{Stage} Date']), 'EC')`, and **Power Automate's `equals()` is
case-sensitive**. Uppercase `EC` matches and is handled correctly; lowercase `ec` falls straight
through to `int('ec')` and throws *"The value cannot be converted to the target type"*.

That is the failure the ~7–8 bad rows have been coming from — not an unguarded column, a
half-guarded one.

**The fix — apply to all six mapped stages** (Coiling, Stacking, Assembly, Drying, Testing,
Finishing; Tanking and Delivery are excluded per A5b), on both `CreateOrderItem` and
`UpdateOrderItem`:

```
{Stage} Status =
  if(equals(trim(item()?['{Stage} Date']), ''), null,
     if(equals(toLower(trim(item()?['{Stage} Date'])), 'ec'), 'In Progress', 'Completed'))

{Stage} End Date =
  if(or(equals(trim(item()?['{Stage} Date']), ''),
        equals(toLower(trim(item()?['{Stage} Date'])), 'ec')),
     null, addDays('1899-12-30', int(item()?['{Stage} Date'])))
```

`toLower()` is the whole change. With it the run completes clean and **A6b's manual fix-up is
not needed at all** — the three lowercase rows get the same `In Progress` treatment as the six
uppercase ones, which is what they always meant.

**Re-scan the fresh snapshot at A6.** This snapshot is from 08-31 09:41 and more units will have
entered coiling since, so expect the count to grow — the *pattern* is what matters, not the
exact nine.

### Also confirmed by the same scan

- **All five parity columns exist in `TableOrders`** — `Technical Notes`, `Info+`,
  `Protector & Switchgear Item #`, `Configuration`, `Section Qty`. A5's mappings all have a real
  source, and the backfill genuinely is free
- **`Section Qty` is clean** — no non-numeric values, so its guard is belt-and-braces, not load-bearing
- **82 table columns vs the viewer's 76** — the difference is exactly the 6 native-formula
  columns (`Price`, `Estimated Delivery Date`, `Price CAD`, `Price USD`, `Navigation Order`,
  `Navigation Model`). `TableOrdersColumnOrder.pq` reconciles perfectly
- **`Unit #` is not a `TableOrders` column** — correctly so, it's parsed out of the `Order`
  string. Not a gap

Scanner kept at `scratchpad/scan.ps1` — re-runnable against the A6 snapshot with `-Root <extracted xlsx>`.

### D1. The uncommitted viewer workbook (10 min, first)

`viewer/workbook/FRM10-12.xlsx` is modified but uncommitted. Find out what that change is
before anything overwrites it — plausibly a mid-flight `Sync-PowerQuery.ps1 -Apply` from an
earlier session.

### D2. ColumnMap rows (25 min) — *blocked on B1*

In `viewer/power-query/ColumnMap.pq`, two separate changes.

**a) The 5 parity columns.** Add 5 `Order Items` entity rows, delete the `PENDING` comment block
(~line 121) and the 5 `Models` "Reference only" rows they supersede. Types: text, text, text,
text, number.

**b) Re-source the planned dates.** Change the `SourceField` on two existing rows, leaving
`WorkbookField` exactly as it is:

| Line | Was | Becomes |
|---|---|---|
| `:162` | `Tanking End Date` → `Tanking Date` | **`Planned Tanking Date`** → `Tanking Date` |
| `:165` | `Delivery End Date` → `Delivery Date` | **`Planned Delivery Date`** → `Delivery Date` |

**The output column names do not change, and no column is added.** `Tanking Date` and
`Delivery Date` are read by other worksheets — `BO Manager.xlsx` pulls `Location`, `Status` and
`Tanking Date` from FRM10-12 — so the 76-column layout stays frozen and every downstream
consumer is untouched.

**This is behaviour-preserving.** Those consumers get a planning date today, because the old
backfill copied the planning value into the End Date field. They get the same planning date
afterwards, from the column that actually means it.

Replace both rows' `Notes` — the current text ("TableOrders only ever had one date per stage -
the completion (End) date") is now actively misleading. Record instead that the raw workbook
column was always a planning date, that the actuals live in `{Stage} End Date` on Order Items,
and that surfacing planned and actual separately in the workbook layout is **deferred future
work** because other worksheets depend on these two column names.

**Why this must ship tonight, with the cleanup deferred**: the cleanup clears the old fabricated
values out of `Tanking End Date`/`Delivery End Date`. While the viewer still reads those fields,
running it would blank a column other workbooks depend on. Repoint first and the cleanup becomes
a safe, non-breaking operation whenever it happens. Doing neither is also consistent — the one
combination that breaks things is cleanup without the repoint.

### D3. Sync and refresh (30 min)

`viewer/scripts/Sync-PowerQuery.ps1`. **Close the workbook first** — `Workbooks.Open` has no
try/catch, so a file lock throws an unhandled COM error, and a 2026-08-31 apply silently failed
this exact way. Dry-run afterward and confirm every query reports *Unchanged*.

Then refresh and confirm the 5 columns populate instead of rendering null.

### D4. Parity check (15 min)

Same columns, same order, same row count as today's FRM10-12. `TableOrdersColumnOrder.pq` is
frozen to the live post-corruption-repair layout precisely so staff see no difference.

Expect exactly two blank columns: `Duplicate`, `Duplicate Order`.

### D5. Deploy in place — the FRM09 fix (30 min, Tier 2)

**Decided 2026-09-01: overwrite the file at the existing Index path.**

`/sites/PioneerPlanificatio/Shared Documents/General/FAB/Revue/FRM10-12.xlsx`

FRM09 and BO Manager both resolve FRM10-12 through the single `Index` row pointing there —
verified against FRM09's actual embedded M (`ImportFromIndex("FRM10-12", "TableOrders")`), not
the docs. Deploying in place means **both keep working with no change to either**, there's no
`Index` row to remember to edit, and read-only enforcement has one obvious target. Deploying
anywhere else leaves them reading a file that has silently stopped changing.

**This is destructive. Snapshot the current file into `live-workbook-data/` before overwriting**
— that snapshot is the rollback.

**Read-only**: break permission inheritance on that file. Staff get **Read**. The refresh
operator keeps **Edit** — a Power Query refresh has to save, so read-only-for-everyone would
break the very thing that keeps FRM09 alive.

### D5b. The daily refresh — owners named 2026-09-01

Without this, in-place deployment still ends with FRM09 frozen — just at fresher data.

**Three owners, decided by the user:**
- **The user** (Soleil)
- **Angelique** — in charge of planning, so the person who most directly feels stale data
- **An automated refresh bot**

That's better than the runbook originally assumed, because it removes the single point of
failure: a manual daily refresh with one owner fails the first day that person is away, and
FRM09 goes stale silently — no error, just data that stops moving.

**Two things the bot specifically needs:**
1. **Write access.** A Power Query refresh has to save, so the bot cannot sit behind the
   read-only permission that staff get. Its account is one of the Edit exceptions from D5.
2. **A no-co-authoring guarantee.** The 2026-08-28 corruption came from a refresh running while
   people had the workbook open for editing. That risk is much lower once the file is read-only
   to staff — read-only viewers don't co-author — but a bot refreshing on a schedule is exactly
   the unattended case that incident warns about. It should verify nobody holds the file open
   before refreshing, and fail loudly rather than force it.

**Still verify a human can do it too.** The bot is the mechanism; the two people are the
fallback for when it breaks, which is the failure mode that actually strands FRM09.

- **Named owner.** Not "someone" — a person, written down
- **Each morning**: open the viewer, run the refresh, confirm it completes, close it
- **Safe in a way the old workbook never was.** The viewer is a full deterministic rebuild from
  SharePoint with no manual data to lose, and the 2026-08-28 corruption came from staff
  co-authoring *while* a refresh ran — which can't happen once the file is read-only to them
- Watch for the one real failure mode: `ImportFromIndex` does a live `Web.Contents` read, so a
  human holding `Archive active.xlsx` or `BO Manager.xlsx` open for editing can fail or stall
  the refresh
- Put the procedure in Track E's docs, not only in this plan

Automating it is on the deferred list. Not tonight — a scheduled refresh on a workbook with 31
connections is not something to debug at 04:00.

### D6. Housekeeping (15 min)

- `FRM10-12/CLAUDE.md` has never mentioned `viewer/` — add it
- Export the sales Power App into `power-apps/`. It's about to carry business-critical fan-out
  logic and is currently undocumented and unbacked-up anywhere
- Commit and push all three repos

---

## Track E — Documentation and presentation

Fully independent. Nothing here can break anything.

### E1. Staff how-to guide

Written for someone who has only ever used the Excel workbook. Plain language, French or
English to match the floor.

- What changed and why, in three sentences
- **How to find your work** — the Production Floor view, what Group-by-Location means, how to
  read the colours
- **How to update a unit** — click, edit, done; no save button, no refresh, no "someone else
  has it open"
- **The Planning view** — same columns as the old workbook, for anyone who wants the familiar layout
- What *not* to do: don't edit the Excel file any more, it's now a read-only mirror
- **"If anything looks wrong or you're not sure — come ask [you]."** By name

Lives on the SharePoint home page (Track B3). Keep it to one screen.

### E2. Visual companion for the presentation

Published page: before/after architecture, what changes for staff day to day, what's live now
versus what's coming (Phase 1 workflow tasks, Monday.com production tracking, the document
library). Something for the room to look at besides a list view.

### E3. Cheat sheet for you

One page, for 09:00 on no sleep:
- The demo click-path in order
- **Known gaps, so nothing surprises you on screen**: `Duplicate` and `Duplicate Order` are
  blank by design; `Primary`/`Secondary Voltage` and `Sales Notes` are mapped but blank in live
  data; whatever Tier 2 items didn't land
- The stale-row count from A7, if it ran — better to state it than be asked

---

## Deferred — record these, don't build them tonight

Write these into `Workflow-Automation/docs/roadmap.md` before the repos are committed, so they
don't survive only in tonight's conversation.

- **Tanking/Delivery cleanup.** Clear the fabricated `Completed` statuses and fake End Dates the
  original backfill wrote. Fully spec'd, with the safety discriminator already designed: a blank
  `{Stage} Start Date` means the value came from the backfill, a populated one means a genuine
  live completion that must not be touched. Safe to run any time once D2 ships.
- **Surfacing planned vs actual separately in the workbook.** The viewer keeps 76 columns
  tonight because `Tanking Date`/`Delivery Date` are read by other worksheets. Exposing the
  actuals as their own columns is a real migration — it needs those consumers identified and
  updated first, `BO Manager.xlsx` among them.
- **`Order Items - BO sync`** — spec'd 2026-08-31, affects 8 of ~1000 rows.
- **`Estimated Delivery Date` computation + daily sweep** — spec'd, blocked on nothing.
- **Phase 1 / `Workflow Tasks`** — all 8 checklist steps.
- **Qty-change handling for the fan-out.** No mechanism exists today either; `Regrouped Into` is
  schema-only and manual. Not a regression, but now a known hole in an automated path.
- **Automate the viewer refresh.** Tonight ships a documented manual refresh. Without one,
  FRM09 and BO Manager freeze at the last refresh.
- **The `Archived` column** is still structurally present in the live workbook's table
  definition — depopulated, not deleted, despite `CONTEXT.md:26` saying it was dropped.

## Verification before you leave

- [ ] Every row from D0's landmine list has been fixed in SharePoint, and no failed iteration
      was left unaccounted for
- [ ] `Tanking Date` and `Delivery Date` in the viewer are populated, not blank, and match what
      the workbook showed before tonight
- [ ] No new `Tanking`/`Delivery` `Status = Completed` was written by the run — spot-check a
      unit that hasn't been tanked
- [ ] Create a real order through the app end to end — units appear, correct Unit IDs
- [ ] Production Floor view: grouped, coloured, no blank Order Numbers
- [ ] Viewer opens with 76 columns, only `Duplicate`/`Duplicate Order` blank
- [ ] Viewer opens **from a normal staff account**, not just yours
- [ ] Old FRM10-12 is read-only to staff
- [ ] Snapshot of the pre-overwrite FRM10-12 exists in `live-workbook-data/`
- [ ] FRM09 refreshes and returns current data — the real proof the in-place deploy worked
- [ ] BO Manager refreshes and returns current `Location`/`Status`/`Tanking Date`
- [ ] The daily-refresh owner is named and knows the procedure
- [ ] Transfer flow is **OFF**; trigger flow is **ON**; fallback copy is **OFF**
- [ ] Test rows deleted
- [ ] All three repos committed and pushed

## Abort criteria

Present Tier 1 and finish the cutover later if, at 05:15:

1. The transfer run failed **beyond** the expected ~8 `int()` rows — throttling, or a failure
   count far above D0's predicted list. The known handful is not an abort condition; it's A6b
2. Reconciliation isn't built and tested — without it, `Active` rows for finished units are
   stranded with no Excel side left to correct them from
3. Viewer parity fails, or it won't open from a staff account
4. Fan-out is unreliable — a half-working Save button is worse than none, since sales depends
   on that app tomorrow morning

None of this is one-way. Tier 1 alone is a genuinely good presentation.
