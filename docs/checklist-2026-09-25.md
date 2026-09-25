# Checklist — Friday 2026-09-25

Carried over from the 2026-09-24 build night. The board
(`docs/build-nights/BUILD-NIGHT-2026-09-24.md`) has the full evidence; this file is what to *do*.

**State going in:** the Order Items trigger flow is **v008, live, and OFF**. It no longer touches
`Status Date` — staff keep entering it by hand. The four sync flows (Order, Models, Model Revisions,
Clients) are clean and on the connection reference. Today's outage left **no** parent→unit drift.

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
- [ ] `Order Items` → `E21007-1/1`: Model lookup → **M-MEEN-0001** (Model Revision already MR-MEEN-0001-V1)
- [ ] If Q1 = typo: correct E21005A's item number where it is kept, and check which model/revision it points at
- [ ] Editing the Models rows fires the Models sync flow → units follow on their own. Re-run `x25` after and check the MEEN units are clean.

---

## 2. Decisions that need an answer (nothing written until then)

| # | Question | Evidence | Answer |
|---|---|---|---|
| D5 | **32 order dates one day apart** (Order Date / Initial Promised Date) on 22140, 22141, 22156, 22157, P00005, P10003 — the Order says the 26th, its units say the 25th. Which date was meant? | E7 on the board (21:42). **Reading: the Order's later date was meant.** Order Date = the order's creation day in 3 of 3 checkable cases (22156 created 09-01, P00005 / P10003 created 09-03); the units' and Excel's copies put it a day *before* the order existed; 22156's earlier promised date is a Sunday. The SharePoint screen shows the earlier date too (UTC midnight displays as the day before on an Eastern site) — that is how Excel and the units inherited it. Only these 6 of 457 orders are stored this way; cause unknown. **If you agree:** rewrite the six Orders' dates as plain dates (then the units follow) | |
| D6 | **~40 units have LDs / Engineering Required = true/false, their Order is now blank.** Units right, or Orders right? | E6 on the board (21:40). **Reading: the units are right — the Orders were never set, not wiped.** Units match FRM10-12 unit by unit (22111: EngReq N on exactly 5/10 and 6/10); the Order already disagreed with Excel at 03:39; LDs/EngReq are plain Yes/No and the 09-11 conversion never touched them (the "conversion window" link was wrong). **Confirm with `scripts/x26_order_flag_history.js`** (read-only) → `copy(window.x26)`: live true/false/blank counts + each order's history. If confirmed: fill the Orders from the units — nothing to fix on the units | |
| D1 | **Livraison**: forcing `Terminé`/`Delivered` on *every* later step change of a delivered unit — intended, or only on the move *into* Livraison? | v008 keeps current behaviour | |
| D2 | Level the stamps with `x24` before enabling the flow, or let Livraison-but-Active units complete on their next edit? | run `x24` dry run first | |
| D4 | If a parent field is now blank but the unit still has a value, should the repair clear the unit? | x22 lists them, never clears | |
| — | `P00005`: Initial Promised Date (2025-12-30/31) is ~8 months **before** its Order Date (2026-09-03) under either reading — likely a year typo (2026-12-31?). Ask its creator (Dominic Laguë) | x25, E7 | |
| — | Models 391/392 give revision ids `MR-ENMA-0052` / `-0053` with **no `-V1`**. Wrong in Model Revisions? | x25, x17 rule | |

---

## 3. Console runs still to do (same browser tab as `x25`; flow stays OFF)

- [ ] **RUN1 apply** — `x22` with `CLI_FILL = true`, `DRY = false`, `OVERWRITE = null`. Expect **1,053 written / 1,053 verified / 0 failed**. *(Skip if already done tonight — check the output.)*
- [ ] **RUN2 dry** — first, in the x25 tab:
      ```
      window.x25OV = window.x25.report.filter(r => !/Date$/.test(r.field) && r.parentV !== "" && r.unit !== "E21007-1/1").map(r => ({unit:r.unit, field:r.field})); window.x25OV.length
      ```
      then `x22` with `CLI_FILL = false`, `OVERWRITE = window.x25OV`, `DRY = true`. Send the output for a check before applying.
- [ ] **RUN2 apply** — same, `DRY = false`, after the dry run is checked.
- [ ] **Re-run `x25`.** Expected left over: only the D5 dates, the D6 LDs/EngReq, and E21007 — nothing else.
- [ ] `x16` (mirror audit) and `x24` dry run (stamps) — paste output.
- [ ] `x17` (Model Revisions `ModelID` audit) — expect 393/394 clean.
- [ ] `x26` (read-only, D6 evidence) — paste `scripts/x26_order_flag_history.js`, then `copy(window.x26)` and paste the result.

⚠️ If the tab was reloaded, `window.x25` is gone: run `x25` again before RUN2.

---

## 4. Turning the trigger flow back on

Only after section 3 is done.
- [ ] Test on a **model-less unit** (edit any field) → run succeeds, nothing breaks.
- [ ] Move a test unit **into Livraison** → Step Status `Terminé`, Item Status `Delivered`.
- [ ] Change a step on a normal unit → `Status Date` is **not** touched (manual now).
- [ ] Enable. Expect a burst of runs as it catches up on tonight's ~1,800 edits — harmless with v008.
- [ ] After a day: delete the stray SharePoint connection `…5348ae66…` (check its *used by* list first).

---

## 5. Small clean-ups (any time)

- [ ] Client names with `§` instead of `&`: `LG§E`, `PSE§G`, `BLACK § McDONALD`, `MADISON GAS § ELECTRIC`,
      `MEMPHIS LG§WATER`, `SMITH § LONG` — rename on the Clients list (the sync pushes it to units).
- [ ] 80 of 97 clients have no lead time — decide whether blank should mean FRM13's generic 26 weeks, and where that default lives.
- [ ] Test client rows `test`, `test2`, `test3` on the Clients list.

## 6. Still parked from 2026-09-21 (not for tomorrow unless there is time)

- Fill the parent columns inside the Power App's unit `Patch` — the real fix for the fan-out race.
- Retry on Save Conflict for the four sync flows' `Update_unit`.
- Error handling on every `Patch` in the Power App.
