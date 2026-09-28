# Viewer-free archive build: status, morning of 2026-09-28

Plan: `~/.claude/plans/rerunning-the-dry-run-snug-lighthouse.md`. Design: `archive-all-lists-design-2026-09-27.md`.
**Nothing has touched the live Archive active.** All work so far is in the repo and on throwaway copies.

## Done and verified (all committed and pushed)

| piece | result |
|---|---|
| Step 0 | Mirror refreshed; the 11 manual list exports moved to `sharepoint-lists/Archive/`; column recipe written |
| **Five new list tables** (agent A) | Order 473, Clients 99, Models 396, Model Revisions 396, Order Items 1,130 rows, built on a copy. **Equal to the live mirror on 258,375 cells** except 6 intended (SharePoint `error;#256` → blank on Order Items 1256/1257 FxYear/FxRate/PriceCAD). A second refresh is additive. Refresh takes 1–8 s per table. |
| **Apply tool** | `scripts/Apply-ArchivePowerQuery.ps1`: copies only, changes queries in place, one table at a time, saves only if everything refreshed and nothing shrank |
| **FRM10-12 query** (agent B, reviewed by C) | Map-driven from Order Items + Order / Model Revisions / Clients (never the copy columns). 111 pinned columns = today's 93 + 18 BO. BO backfill keeps **all 1,391** historical BO values, including the 1,032 on units no longer on SharePoint. Duplicate / Duplicate Order have no SharePoint source, so the archived values are kept. It **evaluates cleanly in Excel**: 111 columns, 5,322 rows, every guard passes, ~140 s. |
| **Review** (agent C) | `archive-pq-review-2026-09-28.md`, 24 findings. Two high-severity silent-loss paths fixed: an unreadable local table would have rebuilt the archive from SharePoint alone and dropped every deleted unit. Now it fails loudly. Every conversion is locale-proof. |
| **Checker** (agent D) | `scripts/check_archive_rebuild.py` + 30 mutation tests. On the copy with the new tables: **PASS, 0 of 8 checks failed**. The Nightly Sync replay matches. |
| **Refresher script** | Step 8 date converter (tonight) + `checkLegacyShapes()`: pinned headers, reports only convertible date text left unconverted, ignores legacy placeholders. 10 + 20 tests pass. |
| Red health items | 30 SharePoint edits + revision 417 recycled. Mirror at 04:5x: **0 red**. |

## 🔴 The one blocker: loading the FRM10-12 table into the Data Model

`TableArchiveFRM10_12` is loaded **through the Data Model** (that's how it has always been built). With the new
query, the load fails:

> Column '134217730' is too large for this instance of SQL Server 2016 … Analysis Services.

What the experiments showed (all on copies):

| experiment | result |
|---|---|
| new query, evaluated to a normal sheet (no Data Model) | ✅ works, 111 columns, max text 515 chars, no nested values |
| old query, same tool, same Data Model load (control) | ✅ works (18 s) |
| new query, only the original 93 columns, typed | ❌ fails |
| new query, all 111 columns converted to text (as the old query delivered them) | ❌ fails |
| new query, only 2 columns (Order, Location) | ✅ works |

So it is **specific to the data of one or more columns**, not the types, the 18 new columns, the tool, or the
Data Model itself. A bisection to find the column was running and **was stopped by the system for low memory**
(each trial runs a hidden Excel of ~1.2 GB). Per the rules it is not restarted without the user.

### Two ways forward (the user decides)

1. **Finish the bisection** (about 7 trials of ~3½ min; `scratchpad/bisect_model.py`, run with nothing else
   open), find the column, fix its values, and keep the Data Model load. The table keeps its id, so no flow change.
2. **Stop loading this table through the Data Model**: load the query straight to the sheet, as the five new
   tables already are. Types then survive the load, so the text-dates problem disappears at its root (the
   refresher's converter stays as a safety net).
   - Cost: the table is recreated, so its internal id changes, and the Nightly Sync's C2 step needs the new
     table id. That's a one-value flow change (v006) through the usual snapshot/paste loop.
   - Readers use the table **name** through `Index` and are unaffected.

Recommendation: **(1) first**, since it keeps everything else as it is. If the cause turns out to be something the
Data Model simply can't take, go to (2), which is cleaner long term anyway.

## ✅ Update 2026-09-28 midday: blocker solved with option 2 (user decision)

- **The bisection found no single bad column:** each half of the columns loads alone, and all together
  fail. Not memory (it fails with 7 GB free), not 32-bit (Excel is x64), not types (all-text fails), not
  the 18 new columns (93 alone fails). A limit inside Excel's data-model engine for this combination.
- **The data model was doing nothing:** 0 relationships, 0 measures, and the one (empty, leftover) pivot
  reads the sheet table. So the user chose **option 2**: `TableArchiveFRM10_12` is loaded straight to the
  sheet, like every other archive table.
- `scripts/Convert-ArchiveFrm1012ToSheetLoad.ps1` does the one-time switch on a copy:
  1. unlink the old table into a seed, and remove its model plumbing;
  2. create the new sheet table with the same name, on the same sheet name and position;
  3. first refresh takes the history from the seed;
  4. set date formats (kept across refreshes), and repoint the pivot;
  5. delete the seed; a second refresh takes history from the table itself.
  5,322 rows × 111 columns, ~87 s per refresh.
- With the detour gone, the mixed columns keep **each cell's native value**: real dates and numbers,
  placeholders as text. History is no longer rewritten into text.
- **Strict check against a mirror refreshed right before it:** of 494,853 cells, 438,237 identical,
  53,859 cleaner, 1,890 newer from SharePoint, 866 intended, **1 regression**. That one is a junk
  `1899-12-31` "zero date" in the Tanking Date of unit 20597-1/1, long off SharePoint; it now shows 00:00.
  0 BO values lost; readers' columns intact; Nightly Sync replay passes.
- **Nightly Sync v006** (staged): its Excel step reads the table **by name** (`TableArchiveFRM10_12`)
  instead of its internal id, which changes with option 2. The connector accepts the name as a custom
  value. Because the name is the same before and after the switch, **v006 can be pasted now**.

## Go-live runbook (user + Claude, ~30 min)

1. **Paste Nightly Sync v006** (`workflow-data/Order Items - Nightly Sync/_outbox/PASTE-ME.json`, the
   usual loop), save, copy the JSON back into `_inbox/`, then **Run** a dry run. Expect the same result as
   before (reading by name works on today's table too).
2. **Download the live Archive active** (SharePoint `General/FAB/Archive/` → ⋯ → Download), into
   `workbooks/`. Claude renames it and archives the previous copies.
3. **Claude builds the go-live copy from it**, all scripted:
   - apply every query and load the five list tables (`Apply-ArchivePowerQuery.ps1`);
   - run `Convert-ArchiveFrm1012ToSheetLoad.ps1`;
   - refresh the mirror, then run `check_archive_rebuild.py --strict` against the downloaded file.
4. **Upload** (at a quiet moment, nobody in the file, not 01:00–02:00): rename the verified copy to
   exactly `Archive active.xlsx`, then in `General/FAB/Archive/` choose **Upload → Files → Replace**. It
   becomes a new version of the same file (same file id). Rollback = ⋯ → Version history → Restore.
5. **Open it in desktop Excel from SharePoint**, replace the Office Script with
   `Office Scripts/Mixed Query Refresher - Live Version.osts`, run it once, save.
6. **Dry run the Nightly Sync** and compare it with the replay. Then: remove `TableArchiveBO` after one
   verified refresh cycle, and switch deletes on (mirror refresh first).

## Not done yet (after the blocker)
- The full checker run with `--strict` on a copy where FRM10-12 has loaded.
- The "rename the table, refresh must fail with NoLocalTable" test.
- The review's proposed items for agent A's files (the tool's Data Model refresh proof, extra buffers), plus
  the clean-up (delete `Query1`, move the obsolete 09-16 drafts to `_obsolete/`).
- Go-live (upload as a new version), then removing `TableArchiveBO` after one verified cycle, then enabling deletes.

## Also for the user
- **`error;#256`**: SharePoint's calculated FxYear/FxRate/PriceCAD show an error on Order Items 1256 and 1257. The
  archive stores those as blank. Worth fixing the two units' inputs on SharePoint.
- **The Nightly Sync stays a dry run** until the new archive has refreshed once on the live file (punch list).
