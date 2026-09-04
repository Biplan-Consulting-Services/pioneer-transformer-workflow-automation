# Build Night 2 — handover summary

> ### 📍 THIS FILE IS THE WORKING BOARD. A TRACKED SNAPSHOT LIVES IN GIT.
> **Tracked copy:** `Workflow-Automation/docs/build-nights/BUILD-NIGHT-2026-09-03.md` — committed
> and pushed. **This path is not, and cannot be, in any git repo:** it sits at
> `Clients/Pioneer Transformer/`, a plain folder *above* the three repos, and git cannot track
> files outside a repo root.
>
> **So the duplication is structural, not an accident — do not "fix" it by deleting either copy.**
> This path is what `~/.claude/session-tracks.json`'s `_night` field points at and what every
> session opens at registration; deleting it breaks that pointer. The tracked copy is what
> survives the machine.
>
> **⚠️ If you append here, RE-HARVEST before you finish:**
> ```
> cd "Clients/Pioneer Transformer"
> cp BUILD-NIGHT-*.md Workflow-Automation/docs/build-nights/
> # then commit + push from Workflow-Automation
> ```
> That copy step is the whole sync obligation. It is the only thing standing between an append
> here and a record that dies with your session. **Keep appending here** — a working board and a
> committed snapshot is the right shape; an undocumented sync obligation was the bug.
>
> **On a conflict, THIS file is newer and the tracked copy is authoritative for what survived.**
> They differ in line endings only (this one LF, the tracked one CRLF after commit), so a raw
> `diff` reports every line as changed — compare sections, not the whole file.

**Written 2026-09-04 02:32 by 🟢 Track B (`order-items-cutover-status`).**
Detail and evidence live in `BUILD-NIGHT-2026-09-03.md`. This is the read-in-the-morning version.

---

## The one thing to know

**The premise every repo doc was built on was wrong.** The Sep 1 board, runbook and cheat sheet
all say the A6 transfer run never happened. It did — verified live against the tenant. Order
Items has been carrying production data since Sep 1, and the Order Creation app's fan-out has
been creating real units for Patrick Vaillancourt and Dominic Laguë since Sep 2.

Nobody recorded the run because the session that would have was killed by a spend limit at
06:38:47, mid-sentence, right after typing *"Updating the board."*

Everything else tonight followed from checking that instead of trusting it.

---

## Ready for Friday ✅

| Deliverable | State |
|---|---|
| **BO tracking on real data** | `Order Items → BO Tracking`. 19 columns, 73 rows imported, grouped `BO` (10) above `OK` (63), sorted by Planned Tanking Date. Verified in-browser. |
| **Boss price view** | `Order → Direction - Prix (demo)`. 11 columns, calculated price columns resolve correctly. Named *(demo)* so it reads as provisional. |
| **Bilingual views guide** | FR + EN, written by 🟠 D. Teaches personal-vs-public, which is the distinction that prevents damage. |

**Departments are already building their own views without a guide** — `Angelique réunion du
lundi`, `Angelique bobinage`, `JF - Test`. That is the strongest evidence the guide is aimed at
a real need, and it happened unaided.

---

## Blocked on you, nothing moves without it

1. **🔵 Track A — Power Automate designer will not render.** Expanding `Apply to each` pegs the
   page hard enough that the browser extension cannot inject. Reproducible in both the new and
   classic designers, through a full reload. It is the size of `CreateOrderItem` +
   `UpdateOrderItem` at ~90 mappings each. **Needs memory freed, or another machine.**
   → Until then: no column mapping, no backfill, and the ~72 blank Order Numbers stay visible
   in the BO view the BO department will be looking at.
   **⚠️ Two different 72s tonight — do not conflate them.** *This* 72 is rows whose
   `Order_Number_TextField` is null, waiting on the trigger flow. The **72** in "Monday
   blocker" below is workbook rows with no `Order Items` row at all. Same number, unrelated
   causes, pure coincidence.

2. ~~**🟠 Track D — `git push` denied by the permission classifier.**~~ **✅ RESOLVED — you
   cleared it at ~02:4x and everything is pushed.** Corrected by 🟠 D; this entry was written
   from state that was already stale. `FRM10-12 3d3a1e3..6de4672` (12 LFS objects, 9.1 MB) and
   `Workflow-Automation 4af2b76..d121364` (1 LFS object, 1.9 MB), plus `b545d4d` after. Verified
   by re-checking rather than trusting the push output: **`git log origin/main..main` = 0 on all
   three repos.** A's forensics, the guides and the view-definitions export are all on GitHub.
   **Nothing of Track D's needs your approval any more.**

3. **Smaller, still yours:** paste the patched Office Script and refresh the viewer; export the
   sales Power App into `FRM10-12/power-apps/` (still `.gitkeep`, and the tenant is the only
   rollback for the fan-out that is creating production data right now).

---

## Monday cutover blocker 🔴

**72 unit rows exist in FRM10-12 with no `Order Items` row at all.** Harmless today because
staff still read FRM10-12. **The moment `Order Items` becomes the source of truth, all 72
vanish from every view.**

*How this number moved during the night, because the earlier figure is still quoted elsewhere:*
🟠 D found **three** (`P20001-1/1`, `P1_001-1/1`, `P20004-1/2`) from the viewer/TableBO gap, and
🟢 B confirmed the same three by live REST match. Both were looking only at BO-valued units, so
both saw a **subset**. 🔵 A then ran the full diff and found 72. **The three are inside the 72.**
Neither earlier finding was wrong — both were partial views, and neither vantage point could
have seen the rest.

**🔵 A correction (02:3x): it is 72 rows, not 3, and it is probably NOT a parsing bug.** Full
title-level diff — all 1039 workbook `Order` values against all 1052 live titles, intersection
967, not a sample. Track D's three are all inside the 72. But:

- **65 of the 72 are a contiguous block of ordinary order numbers** — `22143`(6) `22144`(4)
  `22145`(2) `22146`(5) `22147`(5) `22148`(4) `22149`(4) `22150`(8) `22151`(8) `22152`(10)
  `22153`(4) `22154`(4) `22155`(1) — plus `20877R1-1/1`.
- **Only 6 of 72 have a non-numeric prefix** (`P1_001-1/1`, `P1_002-1/1`, `P20001-1/1`,
  `P20002-1/1`, `P20004-1/2`, `P20004-2/2`). D saw 3 of those 6 from the BO side, a fair
  inference from that vantage point — but a parsing bug would not select 13 consecutive
  ordinary order numbers.

**Most likely cause: the backfill has never reached them.** `22143`–`22155` are the newest
orders in the workbook, and the Sep 1 run did not complete the table (proved: `21965-3/4` has
no Sep 1 version). **So the backfill probably fixes all 72 by itself.**

**Do not investigate a matching bug first, and do not hand-create the rows.** Run the backfill,
then re-diff. Whatever survives is the real bug, and those 6 `P`-prefixed rows are where to
look. On current evidence there may be no bug at all.


Separately, 🔵 A found orphan rows in `Order Items` with no `TableOrders` row — the *opposite*
direction, and the two sets cannot overlap.

**🔵 A correction (02:3x, after this section was drafted): the orphan count is 71, not "~40",
and the 14 app-created rows must NOT be subtracted.** The "~40" was an early figure derived from
the no-Tanking-Date subset only, and it had *already* excluded the 14. The full diff gives
**85 orphans, 71 excluding the 14 app-created**. Subtracting the 14 again would yield 26 and
understate the problem by nearly 3×.

---

## Questions for people, not bugs to fix

- **The 3-part ceiling.** 5 of the 39 units with parts already use all three slots. A 4th has
  nowhere to go and is dropped silently — exactly as in the workbook today. Ask the BO
  department whether a 4th has *ever* happened, not whether it could.
- **`21989-1/1`** records part `AUCUN`, description `RETOUR`, PO `CLIENT`, supplier `VENTES`.
  Someone using a part row to log a customer return. A process question.
- **3 part entries have a part number but no supplier** — BO2 ×2, BO3 ×1. Their data to fix.
- **`Angelique bobinage` has no filter at all** — the only staff-facing view without
  `Item Status = Active`, so Delivered and Cancelled units show alongside live ones. Probably
  deliberate for winding; worth confirming.
- **Angelique's `réunion du lundi` view is byte-identical to `Planning`** — 24/24 fields, saved
  and never customised. She may have wanted help finishing it.

---

## Findings worth keeping beyond tonight

- **REST writes work on this tenant.** 19 field creations and 73 item updates, all 2xx, from a
  site-context session. The `AADSTS700016` PnP block is a third-party AAD app consent issue,
  **not** a general schema-change block. **Four repo docs say otherwise** and send the next
  person to spend an hour hand-clicking. 🟠 D is correcting them.
- **Internal names ≠ display names, and a wrong guess fails silently.** `Tanking End Date` is
  internally `TankingDate` — the word "End" is dropped. `Planned Delivery Date` truncates at 32
  chars. Read from `/fields`; never retype.
- **`Modified`-in-window is unsound for sizing runs on this list.** The Sep 1 run wrote **913+**
  rows, not the 297 first reported — stuck trigger instances have been overwriting `Modified`
  for three days.
- **`Order_Number_TextField` survives only because the fan-out writes it inline.** That single
  decision is why three days of a dead trigger flow has not surfaced as blank Order Numbers on
  Production Floor. Anything touching that path must preserve it.
- **View definitions had never been exported.** Now at
  `sharepoint-lists/view-definitions 2026-09-04 0110.md`. `Overview` was already lost
  unrecoverably; that can now only happen once.

---

## Errors made and caught, because they matter more than the wins

Three claims were reported as fact and later found wrong — **all three caught by re-checking
something already reported**, which is the same discipline the whole night existed to restore.

1. **🟢 B counted 6 whitespace-only cells as real parts** (40/19/8), then posted a confident
   "both were right" reconciliation that was itself wrong. 🟠 D's original 39/17/5 was correct.
   Caught when phantom `" "` parts appeared in the payload about to be written to production.
2. **🟢 B called Angelique's view a tweaked copy.** It is byte-identical. The claim had already
   reached a staff-facing guide before the re-check.
3. **🔵 A reported the trigger flow as ON and theorised about polling rates.** It has been OFF
   since Sep 1. A found and corrected it themselves.

And **🟢 B stamped board entries with estimated times** (`00:41`, `01:00`) instead of reading the
clock — on a board whose first rule is *a claim is not evidence*. Corrected and marked.

**🟠 D also caught that both staff guides tell staff their FRM10-12 edits "will be wiped"** —
false today, and the one sentence that could actually stop production. Bannered, not rewritten.

---

## Track status

| | Track | State |
|---|---|---|
| 🟢 | **B** — SharePoint UI | **COMPLETE.** All tasks done, board closed, timesheet closed. |
| 🔵 | **A** — Power Automate | **BLOCKED** on the designer. All analysis harvested to `docs/transfer-flow-forensics-2026-09-04.md` — six mappings paste-ready, three runbook corrections, pre-computed expected counts. Nothing dies with the session. |
| 🟠 | **D** — Repo | **COMPLETE.** Six tasks resolved, B.6 stolen and delivered, **12 commits pushed** — nothing unpushed on any of the three repos. |

**A.7 is smaller than the runbook claims:** of 35 "misses", 30 were never touched by the Sep 1
run and get fixed *by* the re-run. Only 5 are genuine per-column failures.

---

## If you only do three things tomorrow

1. Free memory / switch machine → unblocks A → mapping → backfill → clears the blank Order
   Numbers before the BO meeting.
2. ~~Clear D's push~~ — **done, 02:4x. Nothing left on one disk.** *(Replacing it as the second
   thing worth doing: **run the backfill, then re-diff before deciding the cutover** — see item 3.)*
3. Decide the Monday cutover knowing **72 unit rows** currently vanish at cutover (🔵 A's
   correction above — not 3), and that the backfill in step 1 will probably fix most of them.

---

## 🔵 Track A — pick up exactly here

**Nothing was changed in Power Automate.** `Order Items - Excel Transfer Flow` is byte-identical
to how the Sep 1 session left it — a node was expanded, no field was opened, nothing saved, and
the designer's spurious "unsaved changes" prompt was discarded. `Order Items - Create or Update
Trigger` is still **Off**, its on/off state untouched.

**Done:** 0.6, A.1, A.2, A.7 (analysis), plus the full two-way title diff.
**Not built:** A.3, A.4, A.5 — blocked on the designer, not on any unanswered question.
**Deliberately dropped** on budget grounds: the `Condition 1 6 1` root cause (symptom confirmed,
flow is Off, harmless), and A.5c.

**Order of work tomorrow:**

1. **Try the designer before assuming it is broken.** The failure was *tooling*, not
   necessarily the app — automation gives up after 5 s, a person will not. Expand `Apply to
   each`, wait a full minute, then click into `CreateOrderItem`. If it renders, A.3/A.5 are
   just typing.
2. **A.3 + A.5** — paste the six mappings from `docs/transfer-flow-forensics-2026-09-04.md` §6
   into **both** `CreateOrderItem` and `UpdateOrderItem`. Read internal names from that doc;
   never retype one from a display name.
3. **A5b before running anything** — confirm `Tanking End Date`, `Tanking Status`,
   `Delivery End Date`, `Delivery Status` are unmapped on both actions. Unverified tonight.
   Trap: the internals are `TankingDate`/`DeliveryDate` — they **drop "End"**.
4. **A.4**, keeping the fan-out's inline `Order_Number_TextField` write intact — that one line
   is the only reason three days of a dead trigger flow never showed on the Production Floor
   view.
5. **Refresh FRM10-12 via the Office Script button only** (never Refresh All / COM
   `RefreshAll`), then run the backfill.
6. **Verify by re-counting populated values, never by run status** — a healthy run reports
   `Failed`, now confirmed empirically. Expected counts are pre-computed in §6.
   **`Protector & Switchgear Item #` will be 0 and that is correct** — it is 100% blank at
   source, so "populated, not blank" is an impossible test for it.
7. **Re-diff both directions**, then turn the trigger flow back on last, per the user's
   sequence — and watch that runs actually start and drain, since 29+ instances were still
   wedged.

**Two live cautions:** a re-run is safe for the 14 app-created rows *today*, but becomes unsafe
the moment a Qty disagreement appears between the app's fan-out and the workbook — check that
before the pre-cutover run. And never size a run by `Modified`-in-window on this list; it gave
a plausible, wrong "297 rows" against an actual ≥913.

**Unresolved, needs the user:** two timesheet gaps (00:30→00:58 and 00:58→02:31) were never
confirmed, so **no rows were opened or closed by Track A** rather than guess at times.

---

## Edit log on this file

- **02:32 🟢 B** — written.
- **02:3x 🔵 A** — corrected the orphan count (71, not "~40"; do **not** subtract the 14 app
  rows), escalated the Monday blocker from 3 rows to 72 with the contiguous-block evidence,
  flagged the two unrelated 72s, added "Track A — pick up exactly here".
- **02:4x 🟠 D** — marked the push resolved and verified it (`git log origin/main..main` = 0 on
  all three repos).
- **02:5x 🟢 B** — rewrote the Monday-blocker lede, which still opened "Three real, active
  orders" and only corrected to 72 four paragraphs down. A skim-read would have taken away the
  wrong number. Removed a superseded "don't hand-create" rationale that A had already replaced
  with a better one.

**Three sessions each corrected the others' numbers tonight, and each corrected their own.**
That is the reason to trust these figures more than the ones in the Sep 1 docs — not because
anyone was careful, but because everything load-bearing was checked by someone who did not
write it.
