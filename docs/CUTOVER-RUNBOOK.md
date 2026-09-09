# Cutover runbook — Order Items

**This is the current one.** Undated on purpose: there is exactly one, and it is this file.
Five earlier documents described the cutover and disagreed with each other; they are now in
`archive/` with a note saying what each was for. Nothing below is inherited from them
without being re-checked against the repo or the tenant.

> **Cutover:** Thursday 2026-09-10, evening.
> **Live now:** transfer flow `v006` · 48 parent columns populated on `Order Items` ·
> 1,117 rows · trigger flow **Off**.
> **Staged, not pasted:** transfer `v007` · trigger `v002` · three N3 flows.
> **Not yet run:** `X2`, `X1`, `N8`.

---

## The one fact the whole plan turns on

**The transfer flow runs once more, then is deleted.** It is not made create-only and it is
not kept as maintenance (user, 2026-09-09).

Three consequences, because earlier plans assumed the opposite:

- **Do not make it create-only.** The final run's whole purpose is to **update** the 1,117
  existing rows with staff's last edits. Create-only guts that branch — it would create new
  rows and silently skip every update.
- **Do not remove the BO mapping or the five `Order` companion writes** (the old `R7`).
  That only matters if a future run could overwrite SharePoint-native edits. There is no
  future run, and the final run *should* carry BO across.
- **N3 is now essential, not an enhancement.** Today the transfer flow refreshes the 48
  parent columns on every run. Once it is deleted, **nothing does** — a parent rename would
  leave the copies stale silently and permanently.

---

## Stage 1 · Before the run

### 1.1 · Run the three remediation scripts, in this order

Each one: open
`https://ermcopower.sharepoint.com/sites/PioneerPlanificatio/_api/web/currentuser`,
`F12` → Console, paste, Enter. If Chrome refuses the paste, type `allow pasting` once.
**All three are DRY RUN by default** — read the summary, then set `APPLY = true` and paste
again.

> 🔴 **Order matters between the first two.** X2 corrects the stale `Location`; X1 *keys on*
> `Location`. Run X1 first and it clears the delivery of 68 genuinely shipped units. X1 has
> a guard that refuses if it detects X2 has not run — do not rely on it.

**1.1a · `scripts/x2_set_delivered.js` — 66 rows.** Marks the archived-and-delivered units
`Delivered` and rewrites their stale `Location`. All 104 orphans meet the rule (archive
`Location = LI` plus a delivery date); 36 already read `Delivered`.
- **excluded, for you:** `21792-3/5`, `21792-4/5` — archive delivery date is **2026-09-24,
  in the future**
- **flagged, included:** 9 still read archive `Status = EC` — `21803-4/8` plus eight
  `22021-*`

**1.1b · `scripts/x1_clear_fabricated_stages.js` — 1,141 stage-clears.** 834 tanking + 307
delivery cleared, **234 kept** (141 tanking + 93 delivery), **nothing held back**.
Clears to **blank, not `Pending`** — `Pending` destroys the very marker the cleanup depends
on.

Fabrication is proven three independent ways, so this is not a judgement call:
`Tanking End Date` is a byte-copy of `Planned Tanking Date` on 921 of 975 rows; 811 of 975
"completed" tanking dates are **in the future**; and `Delivery = Completed` appears with
`Location = Bobinage` on 29 rows.

**1.1c · `scripts/n8_split_status.js` — creates the columns, fills ~249 rows.** Splits the
composite `Status` (`TE-Se-4` → `Terminé` + `2026-09-04`). The code table is read from
FRM10-12's own `List` sheet, not inferred, and all 19 ambiguous `Jui` rows resolve to
*juillet* from each unit's own stage dates, so none need a human.

⚠️ **The count moves — read the dry run, don't match it to a number here.** It was 247 on
09-08 and 249 on 09-09, because staff keep typing. What must be **0** is `PROBLEMS`.

A third value shape turned up on 2026-09-09 and is now handled: a **bare step prefix with
no date** (`b2`, `B3`, on `21832-1/11`, `21995-1/2`, `21998-3/3`). Those set `Step Status`
and leave `Status Date` **blank** — there is nothing to derive a date from, and inventing
one is the exact class of value X1 spent the day deleting. So expect `with Step Status set`
to cover every row, and `with a Status Date too` to be lower by the number of bare rows.

> ⚠️ **N8 must be run again after the final transfer run** — see 2.4. The flow rewrites the
> composite `Status` and leaves the split pair stale, silently.

### 1.1d · Two one-off cleanups — done 2026-09-09

- **Blank rows deleted.** `Order Items` Ids **1132** and **1133** carried no `Unit ID`,
  no order and nothing but column defaults — "New item" saved empty twice. They were
  invisible to X1/X2/N8 (no stage data, no composite `Status`) but would have shown as
  blank rows in every staff view and been pulled into the viewer's `TableOrders`.
- **The two missing Orders created.** `x4_create_missing_orders.js` → `20877R1` (Id 565)
  and `P20002` (Id 566). Both units existed **only** in FRM10-12 and would have ceased to
  exist at cutover, silently. See 2.3.

### 1.2 · 🔴 Prove the viewer BEFORE the run — the last reversible moment

Do this once N8 has run (1.1c) and **before** anything in Stage 2.

**Why here and not in Stage 3.** The point of no return is **2.4, deleting the transfer
flow** — not the run. Up to that point every failure is recoverable: the flow can be
re-run, the lists re-exported, the workbook re-refreshed. After it, a broken viewer means
FRM09 / FRM11 / FRM13 / BO Manager have no maintained source and no way back except
rebuilding the flow from its `.zip`.

The viewer only needs `Order Items` to be in its final *shape*, not its final *data* — and
N8 gives it that. So it can be fully exercised while everything is still undoable.

```powershell
./viewer/scripts/Sync-PowerQuery.ps1 -WorkbookPath ./viewer/workbook/FRM10-12.xlsx -CreateMissing
# read the report, then re-run with -Apply, then refresh the viewer workbook
```

🔴 `-CreateMissing` or the three new queries (`ValueConversions`, `LocationCodes`,
`StatusStampCodes`) are reported `notFound` and **skipped silently**.

**What must be true before you proceed to Stage 2:**

| check | expect |
|---|---|
| the refresh completes without a `ColumnMap.MissingColumns` error | it names any column that moved |
| `Tank`, `ISO Stack`, `ISO Coil`, `Lead Assembly` | `R`, not `TRUE` |
| the five test columns · `SFRA` | `x` · `Y` |
| `Frame` | `Reçu` / `Plaspak`, and **no error** — this one used to throw |
| `Location` | `XT`, not `Extérieur` |
| `Status` | `TE-Se-4` form, rebuilt from `Step Status` + `Status Date` |
| `TableOrders` column count and order | unchanged — the four consumers key on shape |

⚠️ **None of this M has ever been executed.** The structural checks confirm it parses and
that the logic is right in a model; they cannot confirm Power Query accepts it. Most
likely to bite: `Table.ReplaceValue` with two function arguments, `Step Status` /
`Status Date` not arriving under those exact names, and `Status Date` coming through as
`datetime` rather than `date`. All three fail loudly at refresh.

**If it fails:** stop. Do not proceed to Stage 2. Nothing is lost — the viewer is a repo
workbook, the lists are untouched, and the cutover simply moves.

### 1.3 · Freeze the source

1. **Re-export all four lists** — `Order Items`, `Order`, `Models`, `Model Revisions`. This
   is the only data rollback, and taking it *now* rather than days ago is the point.
2. **Staff save and close FRM10-12.** Anything unsaved never reaches SharePoint.
   🔴 **From desktop Excel only.** A browser save corrupted this workbook on 2026-09-09 —
   Excel Online cannot run Power Query and damages the file on every save regardless of
   what was edited. Mechanism and recovery in `../FRM10-12/CLAUDE.md`.
3. **Refresh FRM10-12 via the Office Script button only.**
   🔴 Never `Refresh All`, never COM `RefreshAll`. `TableOrders` reads the sheet table it
   writes back to, and its second step strips six native formula columns
   (`Estimated Delivery Date`, `Price CAD`/`USD`/`Price`, `Navigation Order`,
   `Navigation Model`). A generic refresh re-lands the table without them.

### 1.4 · Paste `v007`

`workflow-data/Order Items - excel transfer flow/_outbox/PASTE-ME.json`.

One mapping — `item/RevModelDescription`, on **both** write actions. This is urgent rather
than tidy: the final run rewrites that column on ~1,000 rows, and the mapping live in v006
re-installs the 110-character JSON blob on the 979 rows already repaired — **undoing R22 as
its last act**.

Expect after paste: Create **122** / Update **130** `item/*` fields, `toLower(` **34**,
`'EC'` **0**. Everything outside that one key is byte-identical to v006.

---

## Stage 2 · The run

**2.1 · Run the flow.** Full table, from the Run button on the detail page, not the canvas.
Click **once** — a second concurrent run conflicts.

**2.2 · Verify by reading data, never by status.**
🔴 **A healthy run still reports `Failed`.** Check stored time-of-day is `04:00`/`05:00Z`,
and read the write action's **raw inputs** in run history.

Since v006 changed how every parent record is read — from `Get item` to a cached
`Get items` filtered in memory — confirm the flattened `Name`/`Value` key form still works.
If it does not, the 5 `Mdl` and 24 `Rev` columns land **blank with no error at all**.

**2.3 · Re-diff both directions.** Expect **71 → 0**.

The six named survivors are all resolved as of 2026-09-09, and the reason they were
missing is worth keeping: `CheckOrderMatch` is `length(Get_Orders) == 1` — *exactly* one.
Four failed it with **0** Order matches and two with **2** (the `P20004` duplicate), which
is why one list of six looked like a single mystery when it was two.

| unit | was | resolved by |
|---|---|---|
| `P1_001-1/1` · `P20001-1/1` | 0 matches | Orders created 2026-09-08; units by `create_missing_units.js` (Ids 1128–1129) |
| `P20004-1/2` · `P20004-2/2` | 2 matches | duplicate Order 487 deleted; units Ids 1130–1131 |
| `20877R1-1/1` · `P20002-1/1` | 0 matches | **`x4_create_missing_orders.js`, 2026-09-09** — Orders 565 / 566 |

🔴 **Anything appearing here is a new problem.** A non-zero count no longer has a known
explanation, which is the point of driving it to zero before the run.

**2.4 · Delete the transfer flow.** Keep the `.zip` — it is the only artifact that
re-imports.

**2.5 · Re-run `n8_split_status.js`.** Idempotent: column creation skips what exists, the
populate pass recomputes and overwrites.

🔴 **Not optional, and the ordering is load-bearing.** Verified against `v007` itself: the
flow writes `item/Status = @item()?['Status']` — the raw composite from Excel — on both
branches, and touches `StepStatus` / `StatusDate` / `StepStatusStamped` on **neither**. So
the run rewrites the composite and leaves the split pair stale.

That now matters twice over, because **the viewer derives `Status` from the split pair**
(`../FRM10-12/viewer/power-query/StatusStampCodes.pq`). The sequence has to be:

```
2.1  run         →  Status rewritten from Excel, split pair now stale
2.5  re-run N8   →  split pair re-synced from the new Status
3.x  viewer      →  derives Status from the split pair
```

Refresh the viewer between 2.1 and 2.5 and it shows yesterday's stamp — silently, because
every value is well-formed. Stage 3 already sits after 2.5; keep it that way.

---

## Stage 3 · The viewer

> 🔑 **Read the `Index` row first.** Every cross-workbook read in the estate resolves through
> one SharePoint list (`Title` → `Path`) on `.../sites/PioneerPlanificatio` — there is not
> one hardcoded workbook URL anywhere. That is what makes this stage a one-row edit, and it
> is also the silent failure: leave the row pointing at the staff workbook and FRM09 / FRM11
> / FRM13 / BO Manager keep reading a file that has **stopped changing**, with no error.
>
> ⚠️ **There are two real files, not one.** The old `Revue/FRM10-12.xlsx` and a separate
> `Revue/Formulaires/FRM10-12.xlsx` created 2026-08-28. The `Index` row currently resolves
> to `Formulaires/`. So a wrong row does not error — it silently reads an abandoned
> workbook. **This row has never actually been read.** Read it before and after.

**3.1 · Already done in 1.2.** The sync and the conversion checks happen *before* the run,
because that is the last point at which a failure costs nothing. Re-refresh here so the
viewer picks up what the final run wrote, but the M itself is already proven. Evidence for
every conversion: `../FRM10-12/docs/viewer-value-conversions-2026-09-09.md`.

**3.2 · Refresh the viewer and check the conversions landed.**

> ✅ **Column names already verified, 2026-09-09.** All 44 `Order Items` and 13 `Orders`
> `SourceField` entries in `ColumnMap.pq` exist on the live lists. `SharePoint.Tables`
> with `Implementation = "2.0"` returns **display** names — proved by the viewer's own
> `GetLookupId([Order Number])` where the internal name is `OrderNumber` — so ColumnMap
> is right to use `"Coiling End Date"` rather than `CoilingDate`.
>
> 🔑 **The `<Stage>Date` trap that broke X1/X2 does not reach the viewer.** That is an
> *internal* name problem, and only the REST scripts and Power Automate use internal
> names. But note the flip side: the viewer is coupled to the **mutable** half. Internal
> names are frozen forever; a display name can be renamed by anyone in list settings, and
> a rename is what created the trap in the first place. It fails loudly at least —
> `ApplyColumnMap` validates up front and names the missing columns.
>
> ⚠️ Export artifact, so nobody re-raises it: a CSV export percent-encodes `#` in headers
> (`Protector & Switchgear Item %23`). Decode before comparing. `Tank` should read `R`, not
`TRUE`; `Location` should read `XT`, not `Extérieur`; `Frame` should read `Plaspak` without
erroring.

**3.3 · Verify `TableOrders` against all four consumers** — FRM09, FRM11, FRM13, BO Manager.
FRM11 is the one to check hardest: it reads ten columns by literal string and its purge rule
tests `Location` in two-letter codes.

**3.4 · Deploy the viewer to `Revue/FRM10-12.xlsx` and repoint the `Index` row** from
`Formulaires/` to `Revue/`.

- **This overwrites the stale twin.** Snapshot it into `live-workbook-data/` first — that
  snapshot is the rollback.
- **Break permission inheritance on the deployed file.** Staff get **Read**. The refresh
  operator keeps **Edit** — a Power Query refresh has to save, so read-only-for-everyone
  breaks the very thing keeping FRM09 alive.

**3.5 · Name the refresh owners.** Decided 2026-09-01, still the plan: **the user
(Soleil)**, **Angelique** (planning, so the person who feels stale data first), and **an
automated refresh bot**. Three, not one, because a manual daily refresh with a single owner
fails the first day that person is away and FRM09 goes stale silently.

The bot needs write access (it is one of the Edit exceptions above) and a no-co-authoring
guarantee — the 2026-08-28 corruption came from a refresh running while people had the
workbook open. It should verify nobody holds the file open and **fail loudly rather than
force it**.

---

## Stage 4 · The flows

> 🔴 **Gate: nothing in this stage until every bulk write is finished.** The trigger flow
> fires one run per row. X1's 1,141 stage-clears, X2's 66 rows, N8's 247 and the final run's
> 1,117 would each fire per-row.

**4.1 · Paste trigger `v002` and enable.** X3 (131 → 11 actions) plus the Status Date
auto-stamp. Watch 15 minutes; **if any run passes ten minutes, turn it straight back off.**

**4.2 · Paste the three N3 flows, one at a time** — they share a throughput bucket.

| flow | trigger list | fan-out filter | fields |
|---|---|---|---|
| `Order Items - sync from Order` | `Order` | `OrderNumberId eq <ID>` | 18 |
| `Order Items - sync from Models` | `Models` | `ModelId eq <ID>` | 5 |
| `Order Items - sync from Model Revisions` | `Model Revisions` | `ModelRevisionId eq <ID>` | 24 |

Re-verified 2026-09-09 (`scripts/verify_n3_flows.py`): field counts 18/5/24 hold, every
target is one of the 48 columns N2 actually created, all 16 Choice/Lookup sources read
`?['Value']`, change-guard line counts match field counts exactly, pagination is 5000, and
there is no bare `select()`.

🔴 `OrdOrderFolder` is deliberately excluded — a hyperlink is an object on both read and
write, the shape was never sourced, and a wrong one either fails every row or writes
nothing.

**4.3 · Retire the two TextField syncs.** `Model Revisions` and `Order` TextField syncs have
been off since 2026-08-21 and N3 makes them redundant. One staff view still displays
`Order_Number_TextField` — retire rather than revive, but check that view first.

---

## Stage 5 · Staff

**5.1 · Warn the supplier-report producers *before* the email.** FRM11 feeds **eight
outside companies** through eight supplier report sheets, and it goes stale the moment staff
stop maintaining FRM10-12. This is the step with a party outside the building.

**5.2 · Send the cutover email.** `cutover-announcement-2026-09-08.md`.
⚠️ Two things unresolved in it: the `[LIEN]` placeholder is blank, and the wording forks
between "live copy" and "frozen snapshot". Both sentences are drafted; the wrong one has
staff making decisions on stale data.

**5.3 · Clear the pre-publication banners.** There are three kinds and they need three
different things — "strip the banners" is not one action.

| guide | banner | what it needs |
|---|---|---|
| `staff-guide-sharepoint.md` · `-fr.md` | 📋 *Draft for review* | **Review with Soleil, then delete the box.** Rewritten 2026-09-09: the two "don't type in the Excel file" instructions are now correct rather than backwards, and a new *What looks different* section covers the fields that changed from a typed letter to a checkbox or dropdown. |
| `views-guide-sharepoint.md` · `-fr.md` | *Where things stand today (2026-09-04)* | **Content fix, not a deletion.** It says FRM10-12 is still live and staff keep using it as before. True until Thursday, false the moment the cutover completes. Replace, don't remove — staff still need a "where things stand" line. |
| `views-guide-sharepoint-fr.md` only | ⚠️ *AVANT PUBLICATION — vérifier trois libellés* | 🔴 **Verify first, then delete.** Not strippable on its own authority — it flags three French UI labels in section 7 that were reasoned, never read. |

For that last one: open the classic view-settings page **in French** and confirm the three
labels read exactly **« Regrouper par »**, **« Réduits »**, **« Limite d'éléments »**. About
30 seconds in the browser, and it is the only banner in the set that nobody currently owns.
It matters more than it looks — staff will search the screen for those exact words, and a
guide naming a button that does not exist makes them doubt the parts that are right. The
rest of section 7 is verified and depends on no label.

---

## Already done — do not redo

| | |
|---|---|
| **R22 data** | 979 of 979 rows verified against the parent. Only the *mapping* was still wrong; that is `v007` |
| **`test calculated column`** | hidden on the list |
| **Staff edit rights** | everyone with site access can edit the lists — confirmed at site level, which is where it is granted |
| **N5 version history** | versioning on, `MajorVersionLimit` 50 |
| **`P20004` duplicate** | Order 487 deleted; one row remains, both units point at it, no dangling lookup |
| **4 skipped live units** | created and verified, Ids 1128–1131 |
| **48 parent columns** | created and populated (`MdlModelID` 1,008 · `RevkVA` 1,006 · `OrdOrderNumber` 1,013) |

## Deliberately out of scope

- **N6 / N7** — Estimated Delivery column and its nightly refresh. They would put wrong
  promised dates in front of customers.
- **The Model Revisions Choice cleanup** — phases out already-bad data; nothing depends on
  it.
- **`Engineering Required` / `LDs` third state** — already flattened at the destination.
  Captured to `reports/three-state-capture 2026-09-09.csv`; the fix, if wanted, is a source
  change after cutover.

## 🔴 The gap nobody owns yet

Once the transfer flow is deleted, the **sales Power App's fan-out** is the only thing
creating `Order Items` rows for new orders. `power-apps/` is still an empty `.gitkeep` — the
component is unexported, undocumented, and the tenant is its only copy, at the moment it
becomes the most business-critical piece of the system. Not Thursday's work. Should not stay
invisible.

## Evidence, if you want it

| file | what |
|---|---|
| `reports/X1 tanking-delivery 2026-09-08.csv` | 1,375 stage-rows, tiered with reasons |
| `reports/X2 reconciliation 2026-09-08.csv` | all 104 orphans with their archive columns |
| `reports/N8 status split 2026-09-08.csv` | all 247 parses, including the `Jui` resolutions |
| `reports/three-state-capture 2026-09-09.csv` | 1,019 units, `Engineering Required` + `LDs` before flattening |
| `docs/r22-mapping-correction-2026-09-08.md` | why the fix every other doc prescribed would have failed silently |
| `docs/source-vs-list-comparison-2026-09-08.md` | MISSING = 0 across all 68 mapped fields |
| `../FRM10-12/docs/viewer-value-conversions-2026-09-09.md` | all 16 `logical` columns, with the row-level verification |
