# Checklist — Friday 2026-09-25

Carried over from the 2026-09-24 build night. The board
(`docs/build-nights/BUILD-NIGHT-2026-09-24.md`) has the full evidence; this file is what to *do*.

**State going in:** the Order Items trigger flow is **v008, live, and ON** (you enabled it before bed; monitored overnight from the mirror, see the board). It no longer touches
`Status Date` — staff keep entering it by hand. The four sync flows (Order, Models, Model Revisions,
Clients) are clean and on the connection reference. Today's outage left **no** parent→unit drift.

## ✅ Your to-do tomorrow

- [ ] **MEG Energy models** (section 1): meet the users; ask Q1–Q5. This includes confirming the E21007-1/1 repoint you
      made earlier (both its lookups now → 0005). Then make the four fixes.
- [ ] **The six one-day dates** (D5): confirm with Patrick (5 of the 6 are his) that the *stored* date is the one meant:
      22140, 22141, 22156, 22157, P10003. Ask Dominic about **P00005**, whose promised date (2025-12-31) is before its order
      date and is probably a year typo. Then rewrite the six Orders' dates as plain dates; the units follow.
- [ ] **LDs / Engineering Required** (D6): ask the users whether these are **per order or per unit**. Excel kept them per
      unit, while SharePoint has them on the Order, and setting the Order pushes the value to every unit. Run `x26` (read-only)
      for the order histories. Then either fill the Orders from the units, or move the fields to the unit level.
- [x] **Change-tracking design**: answered 2026-09-24 (§0 of the design).
- [ ] **Raise the version limit to 500** (D6) on **Order Items** and **Order**: List settings → Versioning settings → *Keep the following number of major versions* = 500 → OK. Two lists, a minute each.
- [ ] *(when ready)* the automation infrastructure for scheduling (D1).
- [ ] **Nightly Sync** (`docs/nightly-sync-review-2026-09-25.md`): read §2–§5 and answer **N1–N5** (§6). Your v001 visits
      all 1,127 units one at a time (~6,800 actions a night → throttled, which is why it runs forever), deletes on the Excel
      archive row alone with no cap or log, and has no TODAY() recalc. v002 (`claude-5b`, E11) will be staged for you to
      paste: double confirmation, a 50-unit cap, a dry-run first night, and the ~4-row TODAY() touch.
- [ ] Delete `test calculated column` from Order Items (it also uses TODAY()).
- [ ] **Trigger flow**: run the section 4 tests, including the loop-confirmation check, then enable it.

---

## 1. With the users — MEG Energy (`E…` orders) models and revisions

**Who to ask:** whoever knows the MEG Energy jobs (sales / engineering). Bring this table.

### What the three sources say

| unit | PO Item # (Excel) | kVA (Excel) | PO (Excel) | Model it should be |
|---|---|---|---|---|
| **E21005-1/1** | 1147005 | 7,500 | MEG-10027 | M-MEEN-0001? |
| **E21005A-1/1** | ⚠️ **1147005** | ⚠️ **1,500** | MEG-10012 | ❓ — see Q1 |
| E21006-1/1, 1/2, 2/2 | 1147006 | 2,500 | MEG-10027 | M-MEEN-0002 ✅ consistent |
| **E21007-1/1** | 1147005 | 7,500 | MEG-10027 | M-MEEN-0001 (lookup says 0005 ❌) |
| E21011-1/1 | 1147011 | 7,500 | MEG-10012 | M-MEEN-0004 ✅ consistent |
| **E21012-1/1** | 1147012 | 1,500 | MEG-10012 | M-MEEN-0005? |

| SharePoint row | client code | kVA | agrees with Excel? |
|---|---|---|---|
| Revision `MR-MEEN-0001-V1` | 1147005 | 7,500 | ✅ |
| Revision `MR-MEEN-0005-V1` | 1147012 | 1,500 | ✅ |
| Model `M-MEEN-0001` | 1147005 | **1,500** | ❌ kVA swapped |
| Model `M-MEEN-0005` | **1147005** | **7,500** | ❌ should read 1147012 / 1,500 |
| Models/Revisions 0002 · 0003 · 0004 | 1147006 · 1147007 · 1147011 | 2,500 · 2,500 · 7,500 | ✅ all agree |

**Reading (not yet confirmed):** two genuinely different transformers — 1147005 at 7,500 kVA and
1147012 at 1,500 kVA. The two *Models* rows have their code and kVA crossed; the Revisions and Excel
are right. The 09-05 dedup worklist had already flagged this pair `REVIEW`.

**✅ Checked live 2026-09-24 22:25 (SharePoint mirror):** Models / Revisions exactly as in the table above.
Two new facts:
- `E21007-1/1` now points **both** lookups at **0005** (Model *and* Model Revision `MR-MEEN-0005-V1` = 1147012 /
  1,500 kVA); on 09-11 its revision still pointed at 0001. **The user repointed it** (before tonight's investigation), and it still needs confirming with the users. Its copied data still reads
  1147005 / 7,500, which is what Excel says, so **the copies look right and both lookups look wrong.**
- Only **4** MEG units exist in Order Items: E21006-1/2, E21006-2/2, E21007-1/1, E21011-1/1. **E21005, E21005A,
  E21012 and E21006-1/1 exist only in Excel**, so Q1 is about Excel and the Models list, not a live unit.

### Questions for the users
- [ ] **Q1 — E21005A:** its item number says 1147005 but its kVA (1,500) and PO (MEG-10012) belong to
      1147012. Is the item number a typo — should it be **1147012**? (This one typo reproduces the
      wrong Models entry exactly, so it is the likely origin.)
- [ ] **Q2 — E21007:** confirm it is **1147005, 7,500 kVA**.
- [ ] **Q3 — E21012:** confirm it is **1147012, 1,500 kVA**.
- [ ] **Q4 — the other MEG units** (E21005, E21006 ×3, E21011): quick confirm the table above is right.
- [ ] **Q5 — any other MEG Energy orders** coming that would use these models?

### Then fix (only after Q1–Q3 are answered)
- [ ] `Models` → `M-MEEN-0005`: code **1147012**, kVA **1,500**
- [ ] `Models` → `M-MEEN-0001`: kVA **7,500**
- [ ] `Order Items` → `E21007-1/1`: Model lookup → **M-MEEN-0001** AND Model Revision lookup → **MR-MEEN-0001-V1** (both point at 0005 now)
- [ ] If Q1 = typo: correct E21005A's item number where it is kept, and check which model/revision it points at
- [ ] Editing the Models rows fires the Models sync flow → units follow on their own. Re-run `x25` after and check the MEEN units are clean.

---

## 1b. LDs / Engineering Required — the orders and the problem

**The problem.** `LDs` and `Engineering Required` are **Order** fields: set once on the Order, then the Order sync
flow copies them to every unit (`Order - LDs`, `Order - Engineering Required` on Order Items). On the orders below
the Order and its units **disagree**. The value exists on some units but not on the Order (or not on all units).
Checked live from the mirror, 2026-09-24 22:25 (before RUN2).

**Group A: LDs set on the units, blank on the Order.** The regular units carry the value; the **SA twin** units
are blank; the Order is blank.

| order | Order LDs | regular units LDs | SA units LDs |
|---|---|---|---|
| 21661, 21665 | blank | **True** ×3 | blank ×3 |
| 21664, 21932, 21981, 21982 | blank | **True** ×1 | blank ×1 |
| 22022, 22023, 22024, 22025, 22026, 22027, 22028, 22029, 22030 | blank | **True** ×1 | blank ×1 |
| 21499, 21523 | blank | **False** ×3 | blank ×3 |

**Group B: Engineering Required on SOME units only, blank on the Order.**

| order | Order EngReq | units |
|---|---|---|
| 22111 | blank | **False** on 5/10 and 6/10 only; the other 8 blank |
| 22088 | blank | **False** on 1/4 only |
| 22046, 22047, 22048, 22049, 22050, 22051, 22052, 22053 | blank | **False** on the regular unit; SA twin blank |

**Group C: the reverse (Order set, SA twins blank).** 21613 (LDs True / EngReq False) and 21749 (LDs True). RUN2
fills these SA twins from the Order tonight.

**How it may have happened (to confirm):**
- *A user set it on the unit instead of the Order*, as you suspect. Either directly in Order Items, or in the old
  Excel, where these were per-unit columns and the transfer flow then carried them in. E6 found the units match the
  FRM10-12 staff workbook unit by unit, which points at the Excel side.
- The **last editor is `soleil.anker` on every one of these units**. The flows and scripts all run under your
  account, so the editor field cannot tell a person from a flow. **The version history timestamp can:** open one
  unit (e.g. `21665-1/3`) → Version history → find when `Order - LDs` became True. If it's in a transfer-run window
  (09-01 06:43–07:31, or the 09-10/11 cutover night), it came from Excel. At any other time, someone edited Order
  Items directly.
- ⚠️ If staff can type into the `Order - …` columns on Order Items at all, that is the real gap. Those columns are
  flow-maintained copies and should be **read-only** in the views and forms.

**To decide with the users:** are LDs / Engineering Required **per order** or **per unit**?
- **Per order:** set the Order, and the flow pushes it to all units, which fixes all three groups. Make the unit
  copies read-only.
- **Per unit** (22111 suggests Engineering Required can differ by unit): these should not be Order fields at all.
  Move them to the unit, and stop the sync copying them.

## 2. Decisions that need an answer (nothing written until then)

| # | Question | Evidence | Answer |
|---|---|---|---|
| D5 | **32 order dates one day apart** (Order Date / Initial Promised Date) on 22140, 22141, 22156, 22157, P00005, P10003 — the Order says the 26th, its units say the 25th. Which date was meant? | E7 on the board (21:42). **Reading: the Order's later date was meant.** Order Date = the order's creation day in 3 of 3 checkable cases (22156 created 09-01, P00005 / P10003 created 09-03); the units' and Excel's copies put it a day *before* the order existed; 22156's earlier promised date is a Sunday. The SharePoint screen shows the earlier date too (UTC midnight displays as the day before on an Eastern site) — that is how Excel and the units inherited it. Only these 6 orders are stored this way; cause unknown. **Live check (mirror 22:25):** 4 orders on Order Date (22156, 22157, P00005, P10003) and 6 on Initial Promised Date (+22140, 22141); all created 08-25 → 09-03, 5 of 6 by Patrick; the stored date = the creation day on 22156 / P00005 / P10003. **Quick confirm with Patrick.** **If you agree:** rewrite the six Orders' dates as plain dates (then the units follow) | |
| D6 | **~40 units have LDs / Engineering Required = true/false, their Order is now blank.** Units right, or Orders right? | E6 on the board (21:40). **Reading: the units are right — the Orders were never set, not wiped.** Units match FRM10-12 unit by unit (22111: EngReq N on exactly 5/10 and 6/10); the Order already disagreed with Excel at 03:39; LDs/EngReq are plain Yes/No and the 09-11 conversion never touched them (the "conversion window" link was wrong). **Confirm with `scripts/x26_order_flag_history.js`** (read-only) → `copy(window.x26)`: live true/false/blank counts + each order's history. If confirmed: fill the Orders from the units. **Live check (mirror 22:25), two patterns:** LDs: regular units hold the value, SA units and the Order are blank (21665: True×3 + SA blank×3). EngReq on 22111 / 22088 / 22046–53: Order blank, only SOME units False (22111: 2 of 10). 🔑 **Ask the users: are LDs / Engineering Required per ORDER or per UNIT?** Excel kept them per unit. Setting the Order pushes the value to ALL its units, so if they can differ per unit they should not be Order fields | |
| D1 | **Livraison**: forcing `Terminé`/`Delivered` on *every* later step change of a delivered unit — intended, or only on the move *into* Livraison? | **Seen live on 09-23** (version history, board 22:38): someone set a delivered unit's step back and the flow forced `Terminé` again 34 s later. v008 keeps this behaviour | |
| D2 | Level the stamps with `x24` before enabling the flow, or let Livraison-but-Active units complete on their next edit? | run `x24` dry run first | |
| D4 | If a parent field is now blank but the unit still has a value, should the repair clear the unit? | x22 lists them, never clears | |
| — | `P00005`: Initial Promised Date (2025-12-30/31) is ~8 months **before** its Order Date (2026-09-03) under either reading — likely a year typo (2026-12-31?). Ask its creator (Dominic Laguë) | x25, E7 | |
| — | Models 391/392 give revision ids `MR-ENMA-0052` / `-0053` with **no `-V1`**. Wrong in Model Revisions? | x25, x17 rule | |

---

## 3. Console runs still to do (same browser tab as `x25`; flow stays OFF)

- [x] **RUN1 apply** ✅ done 2026-09-24 21:5x, 1053/1053 verified — `x22` with `CLI_FILL = true`, `DRY = false`, `OVERWRITE = null`. Expect **1,053 written / 1,053 verified / 0 failed**. *(Skip if already done tonight — check the output.)*
- [x] **RUN2 dry** ✅ 748 fields / 700 writes / 696 units — first, in the x25 tab:
      ```
      window.x25OV = window.x25.report.filter(r => !/Date$/.test(r.field) && r.parentV !== "" && r.unit !== "E21007-1/1").map(r => ({unit:r.unit, field:r.field})); window.x25OV.length
      ```
      then `x22` with `CLI_FILL = false`, `OVERWRITE = window.x25OV`, `DRY = true`. Send the output for a check before applying.
- [x] **RUN2 apply** ✅ 2026-09-24 ~23:05. x22's own read-back died on a SharePoint **503** (throttling), but the **mirror verified it** (23:11 vs 22:25): exactly **748 cells changed on 696 units, 748/748 pairs fixed, 0 new drift, 0 changes outside the synced fields**. Parent drift 822 → 74 = only the held-back D5 dates (32), D6 LDs/EngReq (36) and E21007 (6).
- [x] **Re-run `x25`** — done from the mirror instead (see RUN2): only D5 / D6 / E21007 remain.
- [x] `x16` / `x24`: **done from the mirror 2026-09-24 23:2x.** x16: 3 stale `Model_Revision_ID_TextField` (22097-3/5, 21928-1/5, 21951-1/4 → `M-HYQU-0017`), which self-heal on next edit once the flow is on. x24: 46 step / 43 location stamps off level, **0 units at Livraison not Terminé/Delivered**. With Status Date manual (v008) that is harmless. **No x24 run needed.**
- [x] `x17`: **done from the mirror.** 370/395 match `MR-<model>-Vn`. Exceptions: 15 SA revisions `MRSA-…` (valid); `MR-ENMA-0052` / `-0053` without `-V1` (known); **8 revisions with NO Model link: 414, 415, 416, 417, 419, 420, 421, 422**. 417 is old; **the other 7 are all new since 09-21**, so something (likely the Power App) is creating revisions without their Model. Goes with the deferred Power App check.
- [ ] `x26` (read-only, D6 evidence) — paste `scripts/x26_order_flag_history.js`, then `copy(window.x26)` and paste the result.

⚠️ If the tab was reloaded, `window.x25` is gone: run `x25` again before RUN2.

---

## 4. Turning the trigger flow back on

**You turned it on before bed (2026-09-24).** These are now checks that it behaves, not gates. The overnight loop watch results are on the board.
- [ ] **Loop confirmation test** — *the user confirmed 2026-09-24: the write loop ran Fri 09-18 → Mon/Tue 09-21/22, and they fixed it (the fix is in their v006 edits, so it is in live v008). This test just confirms it.* Unit `21792-3/5` got 46 no-change writes in 30 min on 09-21
      (every ~34 s) — the trigger flow re-firing on its own save. Enable, edit ONE unit, wait 5–10 min,
      and count its versions (the mirror's `VersionCounts`, or the unit's version history). If the count
      keeps climbing, turn it off: it is looping. Check the flow's run history for 09-22 01:05–01:40 UTC
      too — that confirms the cause.
- [ ] Test on a **model-less unit** (edit any field) → run succeeds, nothing breaks.
- [ ] Move a test unit **into Livraison** → Step Status `Terminé`, Item Status `Delivered`.
- [ ] Change a step on a normal unit → `Status Date` is **not** touched (manual now).
- [ ] Enable. Expect a burst of runs as it catches up on tonight's ~1,800 edits — harmless with v008.
- [ ] After a day: delete the stray SharePoint connection `…5348ae66…` (check its *used by* list first).

---

## 4b. Version history — decide after the loop is understood

- 81 units, 30 orders, 25 revisions have already lost their oldest versions (limit is 50 on every list).
  Most of it is no-op loop churn. Stop the loop first, then raise Order Items / Order to 500 (D6 in
  `docs/change-tracking-design-2026-09-24.md`).
- **Power App: a later check, not tomorrow (user, 2026-09-24).** Revision 26: a Power App save (09-17) wrote `ModelID` back to the old `M-HYQU-0009`, undoing the 09-14
  repair — the cause fixed in the app on 09-21. Re-run `x17` to confirm nothing has regressed since.

## 5. Small clean-ups (any time)

- [ ] Client names with `§` instead of `&`: `LG§E`, `PSE§G`, `BLACK § McDONALD`, `MADISON GAS § ELECTRIC`,
      `MEMPHIS LG§WATER`, `SMITH § LONG` — rename on the Clients list (the sync pushes it to units).
- [ ] 80 of 97 clients have no lead time — decide whether blank should mean FRM13's generic 26 weeks, and where that default lives.
- [ ] Test client rows `test`, `test2`, `test3` on the Clients list.

## 6. Still parked from 2026-09-21 (not for tomorrow unless there is time)

- Fill the parent columns inside the Power App's unit `Patch` — the real fix for the fan-out race.
- Retry on Save Conflict for the four sync flows' `Update_unit`.
- Error handling on every `Patch` in the Power App.
