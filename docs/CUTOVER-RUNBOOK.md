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

**1.1c · `scripts/n8_split_status.js` — creates 2 columns, fills 247 rows.** Splits the
composite `Status` (`TE-Se-4` → `Terminé` + `2026-09-04`). All 247 parse; all 19 ambiguous
`Jui` rows resolve to *juillet* from each unit's own stage dates, so none need a human.
The code table is read from FRM10-12's own `List` sheet, not inferred.

> ⚠️ **N8 must be run again after the final transfer run** — see 2.4. The flow rewrites the
> composite `Status` and leaves the split pair stale, silently.

### 1.2 · Freeze the source

1. **Re-export all four lists** — `Order Items`, `Order`, `Models`, `Model Revisions`. This
   is the only data rollback, and taking it *now* rather than days ago is the point.
2. **Staff save and close FRM10-12.** Anything unsaved never reaches SharePoint.
3. **Refresh FRM10-12 via the Office Script button only.**
   🔴 Never `Refresh All`, never COM `RefreshAll`. `TableOrders` reads the sheet table it
   writes back to, and its second step strips six native formula columns
   (`Estimated Delivery Date`, `Price CAD`/`USD`/`Price`, `Navigation Order`,
   `Navigation Model`). A generic refresh re-lands the table without them.

### 1.3 · Paste `v007`

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

**2.3 · Re-diff both directions.** Expect **71 → 6**. The six are already named:
`20877R1-1/1`, `P1_001-1/1`, `P20001-1/1`, `P20002-1/1`, `P20004-1/2`, `P20004-2/2`.
Anything else appearing is a **new** problem.

**2.4 · Delete the transfer flow.** Keep the `.zip` — it is the only artifact that
re-imports.

**2.5 · Re-run `n8_split_status.js`.** Idempotent: column creation skips what exists, the
populate pass recomputes and overwrites. The run in 1.1c is for the pre-run state; this one
re-syncs the split columns against what the final run just wrote.

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

**3.1 · Sync the value conversions into the viewer workbook.**

```powershell
./viewer/scripts/Sync-PowerQuery.ps1 -WorkbookPath ./viewer/workbook/FRM10-12.xlsx -CreateMissing
# read the report, then re-run with -Apply
```

🔴 `-CreateMissing` is **required** — two of the four queries are new, and without it they
are reported `notFound` and skipped silently. The filename *is* the query name in this
script. Full detail and the evidence for every conversion:
`../FRM10-12/docs/viewer-value-conversions-2026-09-09.md`.

**3.2 · Refresh the viewer and check the conversions landed.** `Tank` should read `R`, not
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

**5.3 · Strip the pre-publication banners from the guides** —
`staff-guide-sharepoint.md`, `staff-guide-sharepoint-fr.md`, `views-guide-sharepoint.md`,
`views-guide-sharepoint-fr.md`.

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
