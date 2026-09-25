# Change tracking, error detection and rollback, built on the SharePoint mirror

**Status: DESIGN, awaiting the user's review. Nothing here is built.** Written 2026-09-24 by the planning
session at the user's request: *"create an archiving system so we can track changes and be able to
detect possible errors and roll back if needed"*, and *"design a new archiving system for the new data
workbook"*.

---

## 1. What this is for, and how it relates to the 09-16 archive design

`archiving-architecture-2026-09-16.md` answers **history** questions: what did a unit end up as
(completion records), and what did everything say at a date (monthly snapshots, for audit and DR). It
deliberately rejected daily snapshots, because nobody would ever browse them.

This design answers a different set of questions, the **operational** ones:

| question | example from this project |
|---|---|
| **What changed, when, and who changed it?** | "were the LDs orders modified recently?" (E6, tonight) |
| **Was it a mistake?** | the Status Date erasure (09-14), the 09-01 transfer burst, the fan-out race (09-21), today's outage |
| **Can we undo it, in bulk, safely?** | nothing today. Version history undoes one row at a time, through the UI |

Those questions need **fine-grained changes kept for a short time**. That is exactly where frequent
snapshots are right, so this **complements** the 09-16 design rather than contradicting it:

- the monthly snapshot this design retains **is** the 09-16 Layer 3 snapshot, taken locally;
- the journal (§3) makes the 09-16 Layer 2 *completion records* derivable: a unit's `Item Status → Delivered`
  event is the trigger. Whether to derive them from here is decision D4.

## 2. What already exists, so it is NOT rebuilt

| mechanism | covers | gap |
|---|---|---|
| SharePoint **item version history** | every edit, with who/when/previous value | nobody watches it; restore is one row at a time; **only 50 versions per item** on every list (verified 22:31, step 0; see D6) |
| SharePoint **recycle bin** | deleted items, 93 days | only if someone notices the deletion |
| `flow_version.py` + `.zip` packages | Power Automate definitions | complete; out of scope here |
| **OneDrive** sync of this folder | file-level version history of everything in the repo folder | backup for the files below |
| **the mirror** (`Refresh-SharePointMirror.ps1`, E8) | live lists on disk in ~25 s, raw REST shape, `Columns` catalog | keeps one previous copy only; no comparison |

## 3. The design: three layers on top of the mirror

### Layer A: snapshots (the raw record)
- Every refresh already writes one CSV per list to `sharepoint-lists/mirror/` and moves the previous one
  to `Archive/`. That changes to: **each refresh is a dated folder**,
  `sharepoint-lists/mirror/snapshots/YYYY-MM-DD_HHMM/`, gzip-compressed (~2.4 MB → roughly 0.3 MB).
- **Only the real lists** are snapshotted: Order Items, Order, Models, Model Revisions, Clients, Index,
  Models SA, and the `Columns` catalog. The diagnostic `Order via SharePointTables` table is not.
- **Retention** (D2): every snapshot for **30 days**; after that, keep the **last snapshot of each
  month forever**. That monthly copy is the 09-16 Layer 3.
- **Not in git** (D3). 2.4 MB per refresh would bloat the repo, and OneDrive already versions the
  folder. The latest set stays where the scripts look for it today; the snapshots folder is `.gitignore`d.

### Layer B: the change journal (what changed)
After each refresh, compare against the previous snapshot and **append** the differences to
`sharepoint-lists/mirror/journal/YYYY-MM.jsonl`, one JSON object per change. JSON, not CSV, per the
09-16 reasoning: types survive, and French decimals and lookups don't mangle.

```json
{"asOf":"2026-09-24T22:25Z","prevAsOf":"2026-09-24T22:22Z","list":"Order Items","id":1223,
 "title":"22169-7/10","kind":"change","field":"MdlLatestModelRevision",
 "old":"","new":"MR-HYQU-0093-V1","modified":"2026-09-24T22:24:10Z","editor":"Soleil Anker"}
```

- `kind` is one of `change`, `added`, `deleted` (the row is gone), or `schema` (a `Columns` row was
  added, removed, renamed or retyped).
- Rows are **keyed by list + `Id`, never by Title.** Titles are not unique-safe (x22's Title trap).
- Exclude the columns that change without anyone editing them: `Modified`, `Editor`, versions, ETags.
  Calculated columns are kept but tagged `derived`, so they don't read as edits.
- The journal is small (tonight's whole x22 run would be ~1,800 lines), so it **is kept forever and is
  committed to git**. It is the durable, greppable history.
- ⚠️ **Granularity limit:** if a row is edited three times between two refreshes, the journal sees one
  change, old → final. SharePoint version history keeps the intermediate steps. Layer C falls back to it
  when that matters.

### Layer C1: error checks (is something wrong?)
Run after every journal update and write `sharepoint-lists/mirror/health/latest.md`: a short report,
empty when all is well, and a non-zero exit code for anything red. Each check is one we have actually
needed:

| check | fires when | the incident it would have caught |
|---|---|---|
| **bulk change** | > N rows (default 25) on one field between two refreshes | 09-01 transfer burst; Status Date erasure; tonight's x22 runs (expected; see *acknowledge* below) |
| **value erased** | non-blank → blank on a field that is not normally cleared | Status Date erasure; the LDs question |
| **rows deleted** | any `deleted` event | order 22021's units (09-16) |
| **schema change** | any `schema` event | the `…End Date` renames; columns created by scripts |
| **Index changed** | any change to the `Index` list | production infrastructure with no history at all |
| **invalid choice** | a value not in the column's allowed choices (from `Columns`) | "a plain key into a Choice column" (09-11) |
| **broken lookup** | a lookup id pointing at a row that does not exist | revision 417 |
| **parent drift** | x25's comparison, run from disk | tonight's 818 |
| **mirror / stamp drift** | x16 / x24 logic, from disk | 09-14 stale mirrors |

- **Acknowledge.** Our own planned bulk runs (like tonight's x22) are recorded in
  `health/acknowledged.jsonl`: time window, list, field, reason. A matching bulk change then reports as
  *acknowledged*, not red. Anything unexplained stays red.
- The checks are **Python over the snapshot files**, not formulas in the workbook, so each rule exists
  once and can be tested. They replace the console-only versions of x25/x16/x24 for anything read-only.

### Layer C2: rollback (undo it)
`scripts/plan_rollback.py` selects journal events (by time window, list, field, editor, or an explicit
list) and writes a **restore plan**: `[{list, id, field, expect, restore}]`.

- `expect` is the value the journal says the row holds *now* (the bad value). `restore` is the value
  before.
- **Compare-and-set:** the restore only writes a field if the row **still** holds `expect`. A later
  legitimate edit is reported and left alone, never overwritten.
- The plan is executed by a new console script, `x27_restore.js`, which is list-agnostic. It uses x22's
  guards: dry run by default, quiet output per the E9 rule, read-back verify, a MODE line first. So every
  tenant write stays in the user's browser, like today.
- ⚠️ Restoring a **parent** row (Order, Models…) fires the N3 sync flows, which then push the restored
  value to the units. That is usually what you want; the plan says so explicitly. Restoring
  **Order Items** rows fires the trigger flow when it is on, which is harmless with v008.
- **Deleted rows** are not recreated by this. They come back from the recycle bin, which keeps the
  original `Id` and version history. The plan says so.

## 4. When it runs (D1)

Detection is only as good as how often it looks.
- **Recommended:** Windows Task Scheduler on this PC. Refresh + journal + checks **nightly at 01:30**
  (after the planned 01:00 nightly cleanup / calc touch, which is not deployed yet) and **every 2 h, 08:00–18:00** on workdays.
- **Limit:** it only runs while the PC is on and signed in. Excel COM needs an interactive session.
  A missed run is not data loss: the next refresh compares against the last snapshot, so changes collapse
  into one bigger diff but are not lost.
- **Always-on alternative (later):** a Power Automate export to a SharePoint library, as 09-16 planned.
  Out of scope until the local version has proven the rules.

## 5. Known limits

- **"Who" cannot tell a flow's edit from yours.** The flows run under the user's account. The journal
  records the editor as reported; checks can *infer* a flow from the pattern (which fields changed, in
  a burst after a parent edit), and must say "inferred".
- **Between-refresh granularity** (Layer B note). Version history remains the fine-grained record.
- **Not a backup of the tenant.** It cannot restore a deleted list, a view, a Power App or permissions.
  Views could be added to the snapshot later (E8 item 9) if SharePoint returns them without hanging.

## 6. Build order (each step useful on its own)

0. **Verify version history** is enabled on every list, and read its version limit. The rollback
   fallback depends on it. Add list settings (versioning, limits, item counts) to the mirror as a small
   `Lists` table.
1. **Snapshots:** dated, compressed folders, 30-day + monthly retention, `.gitignore`, and untrack the
   mirror CSVs committed at 22:22 (D3).
2. **Journal:** diff + append, with a test against two known snapshots (tonight's 22:22 → 22:25 pair,
   plus the post-RUN2 refresh, which should show exactly the RUN2 writes).
3. **Checks + health report**, starting with bulk change, erased, deleted, schema, Index.
4. **Rollback planner + `x27_restore.js`**, tested on a mock and then on one real test unit.
5. **Scheduling.**
6. *(optional, D4)* completion records derived from the journal (09-16 Layer 2).

**Acceptance for step 2, the real test:** after RUN2 is applied, one refresh must produce a journal whose
`change` events are exactly the 748 RUN2 fields (old = the x25 unit value, new = the parent value),
plus nothing unexplained.

## 7. Decisions for the user

| # | question | proposed default |
|---|---|---|
| D1 | When should it run? | nightly 01:30 + every 2 h 08–18 on workdays |
| D2 | How long to keep snapshots? | every snapshot 30 days, then one per month forever |
| D3 | Snapshots out of git (OneDrive versions them), journal and health reports in git? | yes |
| D4 | Derive the 09-16 completion records from the journal, instead of a separate flow? | later, after step 3 has run for a few weeks |
| D5 | Bulk-change threshold | 25 rows on one field between refreshes, tunable per field |
| D6 | **Raise the version limit on Order Items?** Step 0 (22:31, mirror `Lists` table): all 7 lists have versioning ON, but at the SharePoint default of **50 major versions**. Every fan-out, trigger run, x22 write and staff edit adds a version to a unit, so a busy unit can lose its oldest history, and with it the fine-grained undo this design falls back on. | raise **Order Items to 500** (and Order to 500), a one-setting change in list settings. Decide after the read-only check of how close units already are to 50. Until then, snapshots are the primary undo record |
