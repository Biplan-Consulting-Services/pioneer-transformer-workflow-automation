# Workspace cleanup and FRM10-12 / FRM09 merge: plan

**Status:** PLAN ONLY, for review. Nothing has been moved, renamed, committed or configured.
Written 2026-09-29 for Punch List item `ws-cleanup-plan` (user 2026-09-28, extended 2026-09-29).
Every number below was measured on 2026-09-29 between 12:00 and 13:00, while a second session was
working in `workflow-data/` and `scripts/`, so the git-status counts are a moving snapshot.

---

## 1. Executive summary

- **Recommended merge shape: one client repo at `Clients/Pioneer Transformer/`**, with
  `Workflow-Automation/`, `FRM10-12/` and `FRM09/` as subfolders **at the paths they already have**.
  No file moves on disk, so none of the 61 cross-folder references (in 31 files) and none of the
  absolute paths (14 hits in 11 WA scripts) break. It also brings the 7 loose client-level files (build-night boards,
  handovers) into git, which ends the manual "harvest" copying.
- **History is kept by `git filter-repo --to-subdirectory-filter`** on scratch clones, then an
  unrelated-histories merge. Every file keeps its full `git log` / `git blame` under its new prefix.
  The cost is that **commit hashes change**, and docs and memory cite them. The mitigation is to commit
  the three `commit-map` files and archive, not delete, the three old GitHub repos.
- **Git LFS is unaffected by the rewrite.** Pointer blobs are unchanged, so the object IDs stay the same.
  The work is to `git lfs fetch --all` first and `git lfs push --all` to the new remote.
  It adds about 185 MB of LFS to the org's quota.
- **What actually breaks: `FRM10-12/scripts/Stage-PowerQuery.ps1`** (it requires `.git` in its own
  folder and uses repo-root-relative `git diff` output), the **frm10-12-pq-workflow skill** (project-level,
  never loaded by sessions that start at the workspace root, and stale), and hash citations.
  Relative paths, absolute paths, timesheet hooks and the Shift Console all keep working.
- **Timesheets: no data change.** The three CSVs and their `_projects.csv` rows stay exactly as they
  are, so past hours stay under what they were billed as. FRM11 already shows that a billing bucket
  doesn't need a repo. Only two sentences of docs change ("named after its repo").
- **The main cleanup is in `Workflow-Automation/docs/`** (77 top-level files, 36 dated, 6 with zero
  inbound references, at least 3 still sitting next to the doc that replaced them). The target is
  about 25 living docs at the top level, with `records/` for point-in-time documents, `archive/` for superseded
  ones, `staff/` for the staff guides, and a `docs/README.md` index.
- **Scripts: index first, move later.** Of 128 top-level scripts, 40 are referenced from nowhere and
  nothing marks which one-offs have run or write to the tenant. The plan adds `scripts/README.md` and a
  `STATUS:` header now. New one-offs go to `scripts/oneoff/`. Existing ones move only in a later batch,
  because 146 path references and 26 `import lib/schema` files would need rewriting.
- **Keeping it clean:** a read-only SessionStart hook (`workspace-hygiene.js`, silent when clean), a
  `supersede` helper that archives, stamps, indexes and relinks in one step, and a client-level
  `CLAUDE.md` "where files go" rule.
- **Effort:** about 13-16 h over 7 phases. Each phase is small, reversible and verified. The merge itself
  (Phase 4, about 3 h) needs **no Pioneer session running** and Excel closed. Two phases need the user:
  GitHub repo creation and archiving, and the doc-archive list.
- **What stays as it is, because it works:** the `Clients/<Client>/` layout, the top-level `Timesheets/`
  and `Claude-Tooling/` repos, `sharepoint-lists/` (dated exports + `Archive/` + mirror),
  the `workflow-data/<flow>/` version system, `rollback/`, `artifacts/`, `power-query/<workbook>/`, and the LFS config.

---

## 2. Current state inventory (measured)

### 2.1 Workspace and client level

| Location | What is there | In git? |
|---|---|---|
| `claude/` (root) | `Clients/`, `Timesheets/`, `Claude-Tooling/`, `.claude/settings.local.json`, plus **4 loose files**: `Add-JiraWorklogs.ps1`, `heures-hors-plafond.html`, `jira-worklog-plan.html` (AFDS Jira time, not Pioneer), `Shift Console.url` | no (plain folder) |
| `Clients/` | only `Pioneer Transformer/` | no |
| `Clients/Pioneer Transformer/` | 3 repos + **7 loose files**: `BUILD-NIGHT-2026-09-03.md`, `-09-03-SUMMARY.md`, `-09-24.md`, `BUILD-NIGHT-STATUS.md`, `HANDOVER-2026-09-05.md`, `HANDOVER-2026-09-08.md`, `TIMEZONE-DECISION-2026-09-04.md` | **no**: git cannot track above repo roots |
| `Timesheets/` | `_projects.csv` (7 rows), 7 project CSVs, `shift-console.html`, `_session-log.md` | own repo (2 modified now) |
| `Claude-Tooling/` | `skills/` (2), `hooks/` (3), `TASKS.md` | own repo. **Verified in sync** with `~/.claude/skills` (`diff -rq` clean) |

Client-level drift, measured with a line-set comparison against `Workflow-Automation/docs/build-nights/`:

| Working file | Lines only in working copy | Lines only in tracked copy | Tracked at all? |
|---|---|---|---|
| `BUILD-NIGHT-2026-09-24.md` | **11** (unharvested) | 0 | yes |
| `BUILD-NIGHT-2026-09-03.md` | 4 | 4 (diverged both ways) | yes |
| `BUILD-NIGHT-STATUS.md` | 1 | 1 | yes |
| `BUILD-NIGHT-2026-09-03-SUMMARY.md` | identical | | yes |
| `HANDOVER-2026-09-05.md`, `TIMEZONE-DECISION-2026-09-04.md` | whole file | n/a | **never** |

### 2.2 The three Pioneer repos

| | Workflow-Automation | FRM10-12 | FRM09 |
|---|---|---|---|
| GitHub | `Biplan-Consulting-Services/pioneer-transformer-workflow-automation` | `.../pioneer-transformer-frm10-12` | `.../pioneer-transformer-frm09` |
| Commits / first / last | 539 / 2026-08-12 / **2026-09-29** | 76 / 2026-08-10 / 2026-09-24 | 6 / 2026-08-11 / **2026-08-17** |
| Branches | main | main | main |
| Tracked files / on disk | 654 / 852 | 111 / 114 | 8 / 11 |
| `.git` size (of which LFS) | 108 MB (82 MB) | 100 MB (98 MB) | 4.9 MB (4.7 MB) |
| LFS files at HEAD / all history | 44 / 57 | 31 / 67 | 3 / 6 |
| Loose git objects (never packed) | **4,216** | 534 | 30 |
| `git status` entries | **31** (34 with `-uall`: 18 M/D, 16 untracked). Mostly the Duke OTD request, the mirror refresh and `_generated/Nightly_Sync_v005-7.json` | 0 | **2**: `workbook/PRO1.FRM09 Winding.xlsx` modified (file dated 08-13), `live-workbook-data/...(Backup).xlsx` untracked |
| `.gitattributes` LFS patterns | pdf xlsx xlsm xlsb xls pbix docx pptx **png vsdx** | same minus png, vsdx | same as FRM10-12 |

On 09-28 the equivalent count was 14 uncommitted/untracked paths. Today it is 31, most of them live
work by the other session.

### 2.3 Workflow-Automation folders

| Folder | Files | Size | Notes |
|---|---|---|---|
| `docs/` (top level) | **77** | 4.0 MB | 73 md, 2 html, 1 pdf (1.8 MB demo cheat sheet), 1 xlsx (`Utilisateurs dossier bleu V2.xlsx`) |
| `docs/archive/` | 6 | | has a good README (what each was, why archived) |
| `docs/build-nights/` | 5 | | tracked copies of the client-level boards |
| `docs/diagrams/` | 1 | | |
| `scripts/` (top level) | **128** | 2.4 MB | 79 py, 41 js, 7 ps1, 1 ts; plus `duke_otd/` (3) |
| `power-query/` | 146 | 508 KB | `Archive-active/` 35 (+7 `_obsolete`), `FRM09/` 4, `FRM10-12/` 23, `FRM11/` 39, `FRM13/` 20, `SharePoint mirror/` 18 |
| `sharepoint-lists/` | 250 | 27 MB | 7 root, 54 `Archive/`, mirror (`live/` 13, `journal/`, `health/`, `snapshots/` git-ignored, 17 x 9 files) |
| `workflow-data/` | 160 | 8.6 MB | 13 loose root files (2026-09-05/07 transfer-flow exports, 2 `.vsdx`, raw outputs) + one folder per flow |
| `workbooks/` | 20 | 66 MB | 7 root (incl. 2 git-ignored `.bak`), 12 `Archive/`, `upload/` 1 |
| `reports/` 11, `rollback/` 10, `artifacts/` 6, `Requests/` 16, `Office Scripts/` 1, `dist/` 7 (git-ignored) | | | |

**Docs, by date and by use.** 36 of 77 top-level names carry a date. Inbound references were counted across
all three repos, excluding the file itself:

| Inbound refs | Docs | Examples |
|---|---|---|
| 0 | 6 | `phases-archive-pass-2026-09-09`, `trigger-flow-v002-paste-sheet`, `n3-choice-conversion-tests-2026-09-11`, `archive-golive-check-2026-09-28`, `archive-live-check-2026-09-28`, `checklist-2026-09-29` |
| 1-2 | 25 | |
| 3-9 | 32 | |
| 10+ | 14 | `roadmap` 47, `infrastructure-overview` 20, `order-items-power-automate-flows` 15 |
| cited in `CLAUDE.md` | **9** | |

Topic clusters that invite "which one is current?": **10** `archive*` docs (about the *Archive active*
workbook, which collides with the folder name `archive/`), 5 `n3-*`, 6 staff guides (3 EN + 3 FR),
4 paste sheets, 2 checklists, 2 trigger-flow, 2 calculated-columns, 2 estimated-delivery.

Docs that say in their own header that they are superseded, but still sit at the top level:
`document-library-plan.md` ("SUPERSEDED 2026-09-14"), `nightly-cleanup-flow.md` ("SUPERSEDED 2026-09-25, never deployed"),
`archive-cover-all-lists-2026-09-16.md` ("Superseded for applying, 2026-09-27"). Also
`checklist-2026-09-25.md`, which `checklist-2026-09-29.md` says it supersedes.

**Scripts, by family** (top level):

| Family | Count | Nature |
|---|---|---|
| `x##_*.js` | 26 (x1-x27, no x3) | browser-console one-offs, **many write to the tenant**. `x27_restore.js` is a reusable tool, not a one-off |
| `n##_*` | 8 + 3 `_*_template.js` | column-build one-offs (N2-N9) |
| `apply_*.py` | 14 | flow-authoring, one per flow version (`apply_d1d2.py` is the documented pattern) + `apply_bo_report_formatting.py` |
| `gen_*.py` | 28 | mix: reusable generators (`gen_nightly_sync`, `gen_data_inventory`, `gen_column_reference`, `gen_handbook_docs`) and single-use ones (`gen_d1d2`, `gen_d3`, `gen_tolower`, `gen_x22_repair`) |
| `check_*` 3, `verify_*` 5, `test_*` 7, `mirror_*` 3, libs (`lib`, `schema`, `load_exports`, `mirror_lib`) | ~22 | tools |
| other (`fix_*`, `create_*`, `migrate_*`, ps1 tools) | ~27 | mixed |

- **40 scripts are referenced from no doc, CLAUDE.md or memory.** 26 of them are only imported or mentioned by other scripts.
- **146** path references (`scripts/<name>`) point at the x##/apply_/gen_/n## families.
- **26** Python files import `lib`/`schema`/`mirror_lib`/`flow_version` from the same folder, so moving a
  script into a subfolder breaks its imports.

### 2.4 FRM10-12 and FRM09 contents, and their duplication with Workflow-Automation

| FRM10-12 folder | Files | Status |
|---|---|---|
| `workbook/` | 1 (+keep) | the **old hand-maintained** workbook, retired as production at the 2026-09-11 cutover |
| `viewer/` (`power-query/` 24, `workbook/`, `scripts/Sync-PowerQuery.ps1`, `office-scripts/`) | 27 | **the production file** that `Index` resolves to |
| `power-query/` (top tree) | 23 | queries of the old workbook. `TableOrders.pq` is known stale (roadmap item 44) |
| `live-workbook-data/` | 14 | dated snapshots 08-11 to 09-04 (26 MB) |
| `linked-workbooks/` | 3 + `Archive/` 1 | Archive active, FRM13 working copy |
| `reports/` 8, `scripts/` 6, `office-scripts/` 5, `Debug/` 3, `docs/` 2, `sharepoint-lists/Index.csv`, `power-bi/PriceReg.pq`, `CONTEXT.md` | | `Debug/` = the 09-09 corruption investigation |
| `.claude/skills/frm10-12-pq-workflow/SKILL.md` | 1 | **project-level** skill (not global, as the Punch List item assumed) |

FRM09: `workbook/` 1, `live-workbook-data/` 2 (+1 untracked backup), `CLAUDE.md`, empty `docs/` and `linked-workbooks/`.
No scripts, no Power Query copy (its 4 queries are tracked in `Workflow-Automation/power-query/FRM09/`).

**Measured duplication:**

| Duplicate | Evidence |
|---|---|
| `Workflow-Automation/power-query/FRM10-12/` (23 files, 09-06 COM export) vs `FRM10-12/power-query/` | **21 of 23 identical** after removing the `// Query:` header and whitespace. The 2 that differ, `ColumnMap.pq` and `TableOrders.pq`, are exactly the drift CLAUDE.md warns about: the export is the workbook truth, the FRM10-12 copy is stale |
| `Workflow-Automation/power-query/Archive-active/{StatusStampCodes,LocationCodes}.pq` vs `FRM10-12/viewer/power-query/` | declared verbatim copies, guarded by `check_frm1012_map.py` (deliberate, keep) |
| Build-night boards | 4 files in 2 places (2.1) |
| `workbooks/Archive active 2026-09-28 1152.xlsx` = `Archive/Archive active 2026-09-27 2356.xlsx` (byte-identical); `FRM10-12 final staff version pre-archive 2026-09-11 0522.xlsx` = `Archive/FRM10-12 2026-09-10 2231.xlsx` | md5 match (only duplicates found across the three repos' Office files) |
| The "never Refresh All" rule | 6 places: WA `CLAUDE.md`, the skill, 4 memory files |
| The `Index` / `ImportFromIndex` explanation | all 3 `CLAUDE.md` + 2 memory files |
| The `SharePoint.Tables` day-early date shift | FRM10-12 `CLAUDE.md`, WA `CLAUDE.md`, 1 memory file |
| "Related repos, separate git repos, documentation only" paragraphs | all 3 `CLAUDE.md` |

`Workflow-Automation/CLAUDE.md` is **432 lines / 31.7 KB**. About 150 of those lines (FRM11, FRM13,
`Index` graph, Inventor/Vault, monday.com) describe the whole estate rather than this repo.

### 2.5 Paths that a move would break

| Kind | Count | Where |
|---|---|---|
| Relative `../FRM10-12`, `../FRM09`, `FRM10-12/<sub>` in WA | **61 in 31 files** | docs (incl. frozen `archive/` and `build-nights/`), `CLAUDE.md`, 1 artifact, 7 scripts, 2 `.pq` headers |
| WA scripts computing `CLIENT/FRM10-12/...` | 5 | `check_frm1012_map.py` (`VIEWER`), `verify_viewer.py`, `gen_data_inventory.py` (glob), `ec_scan.py`, `gen_d3.py` (absolute) |
| Absolute `...\Biplan\claude\...` in code | 11 WA scripts (14 hits), 1 FRM09 file (`.claude/settings.local.json`) | `load_exports.py`, `gen_*`, `duke_otd/build_otd.py`, ... |
| FRM10-12 to WA | 1 | `Build-MissingSharePointOrders.ps1`: `..\..\Workflow-Automation\sharepoint-lists` |
| Script needing its own `.git` | 1 | `Stage-PowerQuery.ps1` (`Test-Path $repo\.git`, `git diff --name-only`) |
| `$PSScriptRoot`-relative (safe under any move that keeps internal layout) | 7 | `Sync-PowerQuery.ps1` x2, `Apply-ArchiveRecovery`, `Compare-ArchiveToLive`, `Fill-RestoredOrderMergeKeys`, ... |
| Memory files citing repo paths or names | 16 of 37 | see 5.5 |
| Pointers outside repos | 2 | `~/.claude/session-tracks.json` `_night` (client-level board path); `settings.json` hooks (Timesheets path only) |
| Hardcoded **dated** filenames already broken by archiving | 3 | **`check_frm1012_map.py` `DEFAULT_BASE` = `workbooks/Archive active 2026-09-27 2356.xlsx`, which now lives in `workbooks/Archive/`**, so running it without `--base` fails. Also `gen_d1d2`/`gen_d3` and `n6`/`_n6_template` (one-offs, harmless) |

> Found while measuring, and left as is because another session owns `scripts/`: the
> `check_frm1012_map.py` default is broken. It is a one-line fix (glob the newest
> `Archive active *.xlsx` across `workbooks/` and `workbooks/Archive/`, or pass `--base`).

---

## 3. Problems found, ranked by day-to-day cost

| # | Problem | Cost today | Evidence |
|---|---|---|---|
| 1 | **Finding the current document** | every session start and every "where is X" | 77 top-level docs, 36 dated, 9 cited by CLAUDE.md, 6 unreferenced, 3+ self-declared superseded docs beside their replacements, "newest dated `checklist-*` wins" is a glob convention in memory rather than a file |
| 2 | **Context weight and rule duplication** | every session loads about 32 KB of WA CLAUDE.md. Rules drift apart | the Refresh All rule in 6 places, `Index` in 5. **The PQ skill predates the viewer**: it points at the top-level `power-query/` tree (not production since 09-11), still lists the `Archived` column (dropped 08-29), and doesn't know `Stage-PowerQuery.ps1` |
| 3 | **Scripts: no "has this run / does it write to the tenant" marker** | risk of re-running a tenant-writing one-off, plus time spent finding the reusable tool among 128 | 26 x## + 8 n## + 14 apply_ at the same level as libs and tools; 40 unreferenced |
| 4 | **Client-level files outside git** | a manual harvest step every build night, and it has already slipped | 11 unharvested lines right now; 2 files never tracked; the "two copies, do not delete either" README exists only because of this |
| 5 | **Split repos for one system** | cross-repo reads, no atomic commits across a change that spans folders, 3 CLAUDE.md to keep consistent | 5 WA scripts read `../FRM10-12`; FRM10-12 reads `../../Workflow-Automation`; 21/23 PQ duplicates; FRM09 has had 6 commits ever, the last on 08-17 |
| 6 | **Archiving breaks pinned filenames** | a silent failure later | `check_frm1012_map.py` default path (2.5). The archive-superseded-copies rule has no "grep scripts for the old name" step |
| 7 | **Long-lived uncommitted work** | risk of loss, and noise for pathspec commits | FRM09 workbook modified since 08-13 (6+ weeks); WA 31 entries |
| 8 | **Inconsistent archive and naming conventions** | small but constant | `docs/archive/` vs `*/Archive/` vs `_inbox/_archive/` vs `power-query/Archive-active/_obsolete/`; `Office Scripts/` (space, caps) vs FRM10-12's `office-scripts/`; `Requests/` capitalised; "archive" is also a domain word (10 `archive-*` docs) |
| 9 | **Git on OneDrive, unpacked** | slower sync (each loose object is a OneDrive file) | 4,216 loose objects in WA, 0 packs |
| 10 | **Stale workspace facts** | misleading context | `settings.json` autoMode says the workspace root "is a git repository ... tracks 0 files" (it is not a repo); memory says "no `gh` CLI" but `gh` 2.98 is logged in as `sankerbaril-biplan` with `repo` scope; the Punch List item calls the PQ skill global (it is project-level) |

**Already fine, don't touch:** `sharepoint-lists/` naming and `Archive/`; the flow version system
(`history.json`, `_inbox`/`_outbox`, `_inbox/_archive`); `rollback/` with its README; `artifacts/` with
its README; `power-query/<workbook>/` with `// Query:` headers; `reports/`; `workbooks/Archive/`; LFS
patterns; Timesheets' one-CSV-per-bucket model; Claude-Tooling's copy-sync (verified in sync). At workspace level,
`Clients/<Client>/`, `Timesheets/` and `Claude-Tooling/` are the right shape.

---

## 4. Proposed target structure

### 4.1 Workspace and client level

```
claude/                                   plain folder (unchanged)
  Clients/
    Pioneer Transformer/                  <- NEW git repo: Biplan-Consulting-Services/pioneer-transformer
      CLAUDE.md                           NEW: estate-wide rules + "where files go" (6.3); loaded for all three folders
      .gitattributes                      NEW: union of the three (adds png, vsdx for FRM folders)
      .gitignore                          NEW: **/.claude/settings.local.json, **/.claude/scheduled_tasks.lock, **/.claude/worktrees/
      build-nights/                       the working boards, now tracked in place (single copy)
        README.md                         moved from Workflow-Automation/docs/build-nights/README.md, trimmed of the two-copies section
        BUILD-NIGHT-*.md, HANDOVER-2026-09-05.md, HANDOVER-2026-09-08.md, TIMEZONE-DECISION-2026-09-04.md
      _merge/                             commit-map-workflow-automation.txt, -frm10-12.txt, -frm09.txt (old hash -> new hash)
      Workflow-Automation/                unchanged path; its own CLAUDE.md shrinks (estate sections move up)
      FRM10-12/                           unchanged path
      FRM09/                              unchanged path
  Timesheets/                             unchanged
  Claude-Tooling/                         + hooks/workspace-hygiene.js, tools/supersede.py, skills/frm10-12-pq-workflow/
```

Rule per level:

| Level | What may live there |
|---|---|
| `claude/` | only `Clients/`, `Timesheets/`, `Claude-Tooling/`, `.claude/`, shortcuts. Anything else is flagged by the hook |
| `Clients/<Client>/` | the client repo's `CLAUDE.md`, `build-nights/`, `_merge/`, and one folder per project. No loose documents |
| `Clients/<Client>/<Project>/` | a project folder, which is a repo root only where the client has one project or projects that share nothing |

### 4.2 Workflow-Automation/docs

```
docs/
  README.md             NEW index (6.4). Every file in docs/, staff/ and design docs has a row
  CHECKLIST.md          the restart checklist, undated, one copy (as CUTOVER-RUNBOOK.md is). Replaces "newest dated checklist-* wins"
  CUTOVER-RUNBOOK.md  roadmap.md  infrastructure-overview.md          (unchanged)
  <living designs, specs, references>   ~22 files, names unchanged even when dated (renaming would break CLAUDE.md and memory)
  staff/                the 6 EN/FR guides (sources of dist/)
  records/              point-in-time and still-true material: checks, reviews, audits, forensics, paste sheets, done plans, test results
    README.md           one line per record
  archive/              superseded: wrong or replaced, do not work from (existing folder and README, extended)
  build-nights/         REMOVED after the merge (single copy at client level)
  diagrams/             unchanged
```

**Rule:** a document is **living** (the one current version of a topic, undated name, top level),
a **record** (true as of its date, never updated again, `records/`), or **superseded**
(`archive/`, with a row in `archive/README.md` naming its replacement). A done plan is a record, not
superseded. `archive/` means "wrong or replaced". Data files don't go in `docs/`: the `.xlsx` goes to `reports/`, and the demo PDF goes to `records/`.

Proposed placement of the 77 current files. **Moves to `archive/` need your OK (open question 4):**

| Destination | Files |
|---|---|
| **archive/** (self-declared or explicitly replaced) | `document-library-plan.md`, `nightly-cleanup-flow.md`, `archive-cover-all-lists-2026-09-16.md`, `checklist-2026-09-25.md` |
| **archive/** (likely, confirm) | `HANDOVER-2026-09-11.md` (memory already calls it "historical"; superseded by the checklists), `demo-cheat-sheet-2026-09-01.md` + its PDF, `visual-companion-2026-09-01.html` |
| **CHECKLIST.md** | rename of `checklist-2026-09-29.md` |
| **records/** (about 34) | paste sheets `a5-d1-d2`, `a5-d3-bo-transfer`, `a5c-tolower`, `trigger-flow-v002`, `n2-column-build-sheet`; checks/reviews `archive-build-status-09-28`, `archive-golive-check-09-28`, `archive-live-check-09-28`, `archive-pq-review-09-28`, `archive-coverage-gap-09-16`, `nightly-sync-review-09-25`, `transfer-flow-code-review-09-08`, `transfer-flow-forensics-09-04`, `pre-cutover-audit-09-09`, `run-verification-09-08`, `source-vs-list-comparison-09-08`, `n3-choice-conversion-tests-09-11`, `n3-fanout-race-09-21`, `n8-transfer-flow-interaction-09-08`, `status-date-null-write-09-14`, `r22-mapping-correction-09-08`, `model-revision-modelid-repair-09-14`, `parent-choice-columns-09-08`, `phases-archive-pass-09-09`, `order-completion-removal-research-09-28`, `sharepoint-as-erp-industry-check-09-16`, `evening-runbook-09-14`, `trigger-flow-v004-fix`, `cutover-announcement-09-08`, `models-dedup-worklist`; done plans `models-sa-fusion-plan`, `archiving-plan`, `phase1-plan`\*, `order-items-build-plan`\*, `order-items-manual-build-checklist`\*, `workflow-tasks-manual-build-checklist`\* (\* = confirm it is done) |
| **staff/** | `staff-guide-sharepoint(-fr)`, `staff-handbook-sharepoint(-fr)`, `views-guide-sharepoint(-fr)` (`gen_handbook_docs.py` input paths to update) |
| **top level, living** (about 22) | `CUTOVER-RUNBOOK`, `roadmap`, `infrastructure-overview`, `column-reference`, `data-inventory`, `lookup-textfield-reference`, `workbook-data-graph-2026-09-06`, `frm11-coupling-analysis-2026-09-06`, `engineering-document-control`, `archive-all-lists-design-2026-09-27`, `archiving-architecture-2026-09-16`, `archive-frm10-12-column-recipe`, `change-tracking-design-2026-09-24`, `order-items-power-automate-flows`, `n3-parent-sync-flow-spec`, `n3-deploy-and-test`, `frm10-12-order-view-spec`, `fanout-powerfx-c2`, `status-date-autostamp-spec`, `calculated-columns-plan`, `calc-columns-port`, `estimated-delivery-date-today`, `analytics-history-options`, `estimated-delivery-date-logic-2026-09-29.html` (untracked, owned by the other session; leave it until committed) |
| **reports/** | `Utilisateurs dossier bleu V2.xlsx` |

Not worth doing: topic subfolders under `docs/` (flows/, archive-workbook/, ...). Once records and superseded
docs are out, about 22 living files plus an index is easy to scan, and a second level would double the
link rewriting for little gain. **Revisit if the top level grows past 35.**

### 4.3 Workflow-Automation/scripts

```
scripts/
  README.md      NEW index (6.4): every script, kind, tenant-writing?, state
  <tools, libs, tests, reusable generators>        stay where they are
  oneoff/        NEW: every NEW x##, n##, apply_vNNN, single-use gen_*, fix_*, create_* from now on
    README.md
  duke_otd/      unchanged (a request-scoped subfolder is the right shape; the model for future requests)
```

**Rule:** a script that will run again (tool, library, test, generator used on every release) stays at
the top level. Anything written for one change goes to `oneoff/`, with the first line
`STATUS: one-off | not run` and, after running, `STATUS: one-off | ran 2026-MM-DD | result: <path>`.
x## numbering stays global (the next is x28). Existing one-offs are **not** moved in this plan
(146 path references, 26 same-folder imports). They are indexed and get the `STATUS:` header. A later batch
can move them once each is marked `ran` (open question 5).

### 4.4 Smaller repo-level fixes

| Fix | Why | Worth it? |
|---|---|---|
| `workflow-data/` root: move the 09-05/09-07 transfer-flow exports into `Order Items - excel transfer flow/` and the 2 `.vsdx` into `docs/diagrams/` | 13 loose files next to a per-flow folder system | yes, small. Wait until the other session is done in `workflow-data/` |
| `Office Scripts/` -> `office-scripts/` | matches FRM10-12 | only together with another move; 1 file |
| `FRM10-12/power-query/` (top tree): add a `LEGACY.md` banner (old workbook, retired 09-11, do not `-Apply`) and **don't** reconcile it | the file it syncs to is no longer production | yes, 5 min. Reconciling the 2 drifted files is not worth it unless the old workbook comes back |
| Drop `Workflow-Automation/power-query/FRM10-12/` as a duplicate | 21/23 identical | **no**: it is the 09-06 ground-truth export cited by `workbook-data-graph`. Add one README line saying so |
| `FRM10-12/Debug/` -> `FRM10-12/live-workbook-data/corruption-test/` | beside the existing corruption test | optional |
| `workbooks/` duplicate `Archive active 2026-09-28 1152.xlsx` (= 09-27 2356) | byte-identical | leave it: the 09-28 name is the one scripts glob for |
| `git gc` in each repo (inside the merge, automatic) | 4,216 loose objects become a handful of packs | yes, it comes free with Phase 4 |

---

## 5. FRM10-12 + FRM09 merge

### 5.1 Shape: client repo (recommended) vs folding into Workflow-Automation

| | **B. Client repo at `Clients/Pioneer Transformer/`** (recommended) | A. Fold FRM10-12 and FRM09 into `Workflow-Automation/` |
|---|---|---|
| Files moved on disk | **none** | FRM10-12 and FRM09 move one level down |
| Relative refs to fix | 0 | 61 in 31 files + 5 scripts + `Build-MissingSharePointOrders.ps1` + both FRM `CLAUDE.md` |
| Absolute paths to fix | 0 | the FRM ones (few), but every memory note and doc "`Clients/Pioneer Transformer/FRM10-12`" changes |
| Client-level boards and handovers | tracked in place; the harvest problem disappears | still outside git, unless moved into WA (which breaks `_night` and the "where someone would look first" signpost) |
| Commit hashes | all three change (mapped) | only FRM10-12's 76 and FRM09's 6 change; WA's 539 stay valid |
| Repo name vs content | `pioneer-transformer`, accurate | `workflow-automation` would hold the workbook repos too |
| Shared CLAUDE.md for estate rules | natural (client level) | at WA level; FRM folders inherit it only because they are nested |
| Against the recorded convention | reverses "one repo per project" for Pioneer | reverses it too, less visibly |

B costs one extra thing, rewriting WA's hashes. A costs dozens of path edits and leaves problem 4 unsolved. Hence B.

**Tool: `git filter-repo --to-subdirectory-filter`, not `git subtree add`.** `subtree add --prefix`
keeps the old commits with their **old root-level paths**, so `git log -- FRM10-12/scripts/Sync-PowerQuery.ps1`
and `git blame` stop at the import commit unless you use `--follow` or subtree-specific tooling. filter-repo
rewrites every commit so the paths are prefixed from the first commit on, and it writes a commit-map.
It isn't installed yet (`pip install git-filter-repo`; git 2.32 is new enough). It runs only on scratch clones, never on the live repos.

### 5.2 Step by step (Phase 4)

**Preconditions (all must hold, checked at the start):**
1. No Claude session open in any Pioneer folder (`session-tracks.json`, the build-night board, and ask the user).
   Excel closed (`tasklist | grep -i excel` is empty): a tracked binary locked by Excel is what broke the 09-25 reset.
2. All three working trees committed and pushed by whoever owns the changes. That includes WA's 31 entries and
   **FRM09's modified workbook since 08-13** (the user decides: commit or discard).
3. Client-level boards harvested one last time (the 11 lines in `BUILD-NIGHT-2026-09-24.md`), using the superset check in `build-nights/README.md`.

**Build (in a scratch folder outside OneDrive, e.g. `C:\pioneer-merge\`, nothing live is touched):**

| # | Command / action | Verify |
|---|---|---|
| 1 | In each live repo: `git lfs fetch --all origin` | `git lfs ls-files --all` count matches 57 / 67 / 6 and `git lfs fsck` is clean |
| 2 | `GIT_LFS_SKIP_SMUDGE=1 git clone --no-local <repo> C:\pioneer-merge\<name>` x3, then copy `.git/lfs/objects` from each live repo into its clone | clone `HEAD` = live `HEAD` |
| 3 | In each clone: `git filter-repo --to-subdirectory-filter Workflow-Automation` (resp. `FRM10-12`, `FRM09`) | `git ls-files` all prefixed; `.git/filter-repo/commit-map` exists |
| 4 | `git init C:\pioneer-merge\pioneer-transformer`; first commit with the root `.gitattributes` (union), `.gitignore`, placeholder `CLAUDE.md` | |
| 5 | For each clone: `git fetch <clone> main` then `git merge --allow-unrelated-histories FETCH_HEAD -m "Merge <name> history (filter-repo, prefix <name>/)"` | no conflicts possible (disjoint prefixes, except root files from step 4) |
| 6 | Copy each clone's `.git/lfs/objects` into the new repo; add `_merge/commit-map-*.txt` and commit | `git lfs fsck` clean; `git lfs ls-files --all` = 57 + 67 + 6 minus shared OIDs |
| 7 | **Tree identity check:** `git rev-parse <oldrepo>:` equals `git rev-parse HEAD:Workflow-Automation` (and the same for FRM10-12 and FRM09) | identical tree hashes, which proves byte-identical content |
| 8 | `git log --oneline -- FRM10-12 \| wc -l` = 76, `-- FRM09` = 6, `-- Workflow-Automation` = 539 | counts match |
| 9 | `git gc --aggressive` | loose objects about 0 |

**Swap (the only step that touches the live folders; about 2 minutes):**

| # | Action | Verify |
|---|---|---|
| 10 | Move `Workflow-Automation/.git`, `FRM10-12/.git`, `FRM09/.git` **out of OneDrive** into `C:\pioneer-merge\backup\` (not deleted) | the three folders are now plain folders |
| 11 | Move the new `.git` to `Clients/Pioneer Transformer/.git`; run `git reset -q` (rebuilds the index from HEAD, doesn't touch working files) | `git status` at client root: **zero modified**; untracked = the 7 client-level files + the 3 ignored `.claude` locals only |
| 12 | `git mv`-free tracking of the boards: create `build-nights/`, move the 7 client-level files into it, `git add`; delete `Workflow-Automation/docs/build-nights/` (a superset check first: the tracked copies have 4+1 unique lines, so merge those in by hand before deleting) | one copy of each board |
| 13 | Update `~/.claude/session-tracks.json` `_night` to `Clients/Pioneer Transformer/build-nights/...` | statusline shows the track |
| 14 | Create `Biplan-Consulting-Services/pioneer-transformer` (private), `git remote add origin ...`, `git push -u origin main`, `git lfs push --all origin` | the GitHub file count and a random LFS file download |

**Fix-ups (Phase 5), each one commit:**

| What breaks | Fix |
|---|---|
| `Stage-PowerQuery.ps1`: `Test-Path $repo\.git` throws | replace with `git -C $repo rev-parse --show-toplevel` and add `--relative` to both `git diff` calls (so paths stay `viewer/power-query/...`). `git ls-files --others` is already cwd-relative. Verify with a dry run against a known change set |
| frm10-12-pq-workflow skill: project-level, loaded only when a session starts inside `FRM10-12/` (sessions start at the workspace root, so it has effectively never loaded; it isn't in this session's skill list either) | move it to `~/.claude/skills/frm10-12-pq-workflow/` + a copy in `Claude-Tooling/skills/` (the existing sync model), with full paths from the workspace root. **Correct the content**: two trees (viewer = production), `Stage-PowerQuery.ps1`, drop the `Archived` column mention |
| Commit hashes cited in docs, memory and boards | not rewritten. The client `CLAUDE.md` says: "a short hash from before 2026-10-xx is an old-repo hash. Look it up in `_merge/commit-map-*.txt`, or open the archived repo" |
| `git log` inside `Workflow-Automation/` now shows all three folders | use `git log -- .` in a folder. Say so in the client CLAUDE.md |
| **The index is now shared across all three folders**: a session in FRM10-12 and one in WA share it | pathspec commits (`git commit -m ... -- <paths>`) become mandatory everywhere. Update the memory note and the client CLAUDE.md |
| 3x "Related repos ... separate git repos, documentation only" sections | replace with "Related folders"; move the estate-wide material (WA CLAUDE.md lines about 242-395: FRM11, FRM13, the `Index` graph, Vault, monday.com, plus the Refresh All, web-reorder and `SharePoint.Tables` rules) into the client `CLAUDE.md` once. WA CLAUDE.md goes from 432 lines to about 250 |
| `FRM10-12/CLAUDE.md` "Working notes: separate git repo", FRM09 idem | delete those lines |
| FRM09 `.claude/settings.local.json` (absolute path), `scheduled_tasks.lock`, `worktrees/` | ignored by the root `.gitignore`. No edit needed |
| Timesheets | **nothing breaks** (the hooks scan every CSV; nothing maps cwd to project). Doc wording only, 5.4 |
| Claude Code memory folder | keyed on the launch folder (the workspace root), which isn't a repo and doesn't move. **Verify** after the first post-merge session that it still reads `C--Users-solei-OneDrive-Documents-Biplan-claude/memory` |
| `new-project-scaffold` | unaffected for new clients. Add a TASKS.md item: a "folder in an existing client repo" mode |

**Retire the old repos (Phase 6, user decision, at least 2 weeks after the push):** push one final commit to each old
repo with a `MOVED.md` ("now `pioneer-transformer/<prefix>/`, hash map at `_merge/`"), then **archive**
(read-only), never delete: old hashes stay resolvable on GitHub. Delete `C:\pioneer-merge\backup\` only after that.

### 5.3 Rollback

| Point reached | Rollback |
|---|---|
| Steps 1-9 | nothing live changed. Delete `C:\pioneer-merge\` |
| Steps 10-13 | delete `Clients/Pioneer Transformer/.git`, move the three `.git` folders back from `backup\`, revert `_night`. Working files were never modified, so this is the exact prior state. If step 12 ran, move the 7 files back to the client root |
| Step 14 (pushed) | same as above. The old GitHub repos are untouched until Phase 6, so pushing to them resumes as before. Delete or archive the new repo |
| Phase 5 fix-ups | each is its own commit: `git revert <sha>` |

### 5.4 Timesheets: attribution stays as billed

- **No change** to `pioneer-transformer-frm10-12.csv` (18 rows), `pioneer-transformer-frm09.csv` (3 rows),
  `pioneer-transformer-workflow-automation.csv` (107 rows) or their `_projects.csv` rows and colours.
  The Shift Console keys `DATA.projects` on these filenames, so renaming would orphan past rows.
- Wording to change: `Timesheets/CLAUDE.md` ("One CSV per project, named after its repo") and
  `timesheet-logging/SKILL.md` line 20 and lines 98-101 ("lands in one project's repo") become "a billing
  project; it need not have its own repo (FRM11 never had one; FRM10-12 and FRM09 were merged into the
  `pioneer-transformer` repo on <date>). Bill by what the work is for, not by which folder it touched."
  Copy the skill change into `Claude-Tooling/skills/`.
- Future billing split: open question 2.

### 5.5 Memory files to update after the merge (read-only for this plan)

| File | Change |
|---|---|
| `workspace_repo_structure.md` | Pioneer is a client-level repo (rationale reversed by the user 2026-09-28); `gh` now works; new repo name |
| `pioneer-transformer-frm10-12.md` | GitHub repo archived, now `pioneer-transformer/FRM10-12/`; commit ids in it are old-repo ids (map in `_merge/`) |
| `pioneer-transformer-frm09.md` | same |
| `pioneer-transformer-workflow-automation.md` | repo name; "start from `docs/CHECKLIST.md`" (was `docs/checklist-2026-09-29.md`, "newest dated wins") |
| `MEMORY.md` | the same two index lines |
| `pioneer-build-night-status-board.md` | the board is at `Clients/Pioneer Transformer/build-nights/`, tracked, single copy; delete the "cannot be tracked, harvest manually" paragraph |
| `feedback_git_pathspec_commit_shared_index.md` | the shared index now spans WA, FRM10-12 and FRM09 |
| `feedback_use_existing_pq_tooling.md` | skill location; mention `Stage-PowerQuery.ps1` and the viewer tree |
| `feedback_archive_superseded_copies.md` | add: "then grep `scripts/` for the old filename" (the `check_frm1012_map.py` regression) |
| `claude-tooling-repo.md` | new hook, tool and skill mirrored there |
| `timesheets-shift-console.md` | the CSV naming wording |
| Verified unaffected (WA-internal paths that don't move) | `pioneer-sharepoint-mirror`, `feedback_snapshot_before_changes`, `sharepoint-writes-via-chrome`, `pioneer-punch-list`, `feedback-frm10-12-refresh-method`, `feedback_ask_before_touching_tenant`, `feedback_verify_against_docs_not_memory` |

---

## 6. Keep-clean mechanisms

### 6.1 SessionStart hook: `workspace-hygiene.js`

- **Live:** `~/.claude/hooks/workspace-hygiene.js`. **Tracked:** `Claude-Tooling/hooks/workspace-hygiene.js` + `hygiene-hook.json` snippet.
- **Registered** as a second entry under `SessionStart` in `~/.claude/settings.json`, `timeout: 10`, `|| true`.
- **Read-only, silent when clean.** Output goes through `additionalContext`, at most 10 lines, then `+N more: run node workspace-hygiene.js --report`.
  Failures and warnings only, per the console-output rule. A `--report` CLI flag prints the full list.
- Runs only when cwd is under the workspace root (same guard as the timesheet hooks). No `git status` over 3 s; skip that check on a timeout.

| Check | Scope | Flags when |
|---|---|---|
| Loose files | `claude/`, `Clients/<Client>/` | any file not on the allow-list (4.1) |
| Unindexed docs | each `docs/`, `docs/staff/` | a file with no row in `docs/README.md` |
| Dead index rows | `docs/README.md`, `scripts/README.md`, `archive/README.md` | a row naming a missing file |
| Dated doc at the top level | each `docs/` | a `YYYY-MM-DD` name older than 14 days whose index row isn't `living` |
| Doc sprawl | each `docs/` top level | more than 35 files |
| Unindexed scripts | each `scripts/`, `scripts/oneoff/` | a file with no row in `scripts/README.md` |
| One-off without a header | `scripts/oneoff/` | first 3 lines lack `STATUS:` |
| Superseded copies | `workbooks/`, `sharepoint-lists/`, `linked-workbooks/`, `live-workbook-data/` roots | 2+ files with the same base name minus the timestamp, outside `Archive/`; any `(1)`/`(2)` download suffix |
| Pinned missing file | `scripts/*.py|js|ps1` string literals matching `(workbooks|sharepoint-lists)/.*\d{4}-\d{2}-\d{2} \d{4}\.(xlsx|csv)` | the file isn't there (it would have caught `check_frm1012_map.py`) |
| Stale uncommitted work | each repo | a modified or untracked tracked-type file older than 72 h (it would have caught FRM09's 08-13 workbook) |
| Tooling drift | `~/.claude/skills/*`, `~/.claude/hooks/*` vs `Claude-Tooling/` | content differs |

### 6.2 Supersede-and-archive helper: `supersede.py`

`python "<workspace>/Claude-Tooling/tools/supersede.py" OLD [--by NEW] [--to archive|records] [--dry-run]`
(the live copy lives with the tooling. It's generic, not Pioneer-specific.) In one step it:

1. `git mv` OLD to `docs/archive/` (or `docs/records/`).
2. Prepends a banner: `> SUPERSEDED <date> by NEW. Kept for its reasoning; do not work from it.` (for records: `> RECORD, true as of <date>.`)
3. Adds or updates the row in `archive/README.md` (file, what it was, replaced by, date) and removes it from `docs/README.md`.
4. Rewrites relative links **to** OLD in living docs, CLAUDE.md files, artifacts and scripts, and rewrites OLD's own outbound
   relative links for its new depth. **Leaves `archive/`, `records/` and `build-nights/` content untouched** (frozen evidence).
5. Prints the memory files and absolute-path mentions that cite OLD, for a manual edit (memory is edited by hand, never by the tool).
6. `--dry-run` shows everything and changes nothing. It never commits: the caller does a pathspec commit.

The same tool with `--data` handles a superseded workbook or export: it moves it to that folder's `Archive/` and
greps scripts for the old filename (the regression in 2.5).

### 6.3 CLAUDE.md rule text (client-level `CLAUDE.md`, section "Where files go")

```markdown
## Where files go

- **docs/ top level = living documents only**: one current version per topic. A new document that
  replaces another is not saved beside it: run `supersede.py OLD --by NEW` in the same commit.
- **Point-in-time documents** (checks, reviews, audits, forensics, test results, paste sheets,
  handovers, finished plans) are dated and go in `docs/records/`. They are never updated after
  the day they describe; write a new record instead.
- **The restart checklist is `docs/CHECKLIST.md`.** Overwrite it; don't write `checklist-<date>.md`.
- **Every new doc or script gets its index row** (`docs/README.md`, `scripts/README.md`) in the
  same commit as the file.
- **New one-off scripts go in `scripts/oneoff/`**, first line `STATUS: one-off | not run`, updated to
  `ran <date> | result: <path>` after it runs. Anything that writes to SharePoint says so in its
  index row.
- **Nothing is saved at `Clients/Pioneer Transformer/` top level** except this file,
  `build-nights/` and `_merge/`.
- **Archiving a dated workbook or export?** Use `supersede.py --data`, which also greps `scripts/` for the old
  filename. Scripts glob for the newest copy; they never pin a timestamp.
- **Commits are pathspec commits** (`git commit -m "..." -- <paths>`): this repo's index is shared
  by every session working in any of its three folders.
```

### 6.4 Index formats (parsed by the hook: first column = filename, backticked)

`docs/README.md`:

```markdown
# docs index
Start with `CHECKLIST.md`, then `roadmap.md`. Superseded: `archive/README.md`. Records: `records/README.md`.

| File | Kind | Status | Topic | Notes |
|---|---|---|---|---|
| `roadmap.md` | living | current | all | master list of work items; not a status report |
| `archive-all-lists-design-2026-09-27.md` | design | current | archive workbook | dated name kept: cited by CLAUDE.md |
```
Kind is one of `living`, `design`, `spec`, `reference`, `guide`, `runbook`. Status is one of `current`, `plan`, `built`.

`scripts/README.md`:

```markdown
| Script | Kind | Writes to tenant? | State | Notes |
|---|---|---|---|---|
| `Refresh-SharePointMirror.ps1` | tool | no (reads) | reusable | run at session start |
| `x27_restore.js` | tool (console) | **yes** | reusable | dry by default |
| `x14_step9_healthy_unit.js` | one-off (console) | **yes** | ran 2026-09-2x | |
```
Kind is one of `tool`, `lib`, `test`, `generator`, `one-off (console)`, `one-off (authoring)`. State is `reusable`, `not run`, `ran <date>` or `superseded by <x>`.

---

## 7. Migration sequence

| Phase | What | Effort | Needs the user | Concurrent session OK? | Verify | Reverse |
|---|---|---|---|---|---|---|
| **0. Decide** | answer section 8; harvest the 11 board lines; FRM09's workbook: commit or discard | 15 min | **yes** | yes | | |
| **1. Indexes + hook (report-only)** | write `docs/README.md`, `scripts/README.md` (about 130 rows, state from git log and docs), add `STATUS:` headers to the one-offs, build `workspace-hygiene.js` with `--report` and register it | 3-4 h | no | yes, new files and header lines only; pathspec commits; skip files the other session has open | hook output lists exactly the known gaps; clean run < 1 s | remove the hook entry; delete the two READMEs |
| **2. docs/ cleanup** | build `supersede.py`; `--dry-run` for the whole 4.2 table; apply in batches (archive, records, staff, CHECKLIST); fix `gen_handbook_docs.py` input paths | 2-3 h | confirms the archive list | **no** session writing `docs/` (about 45-min window) | no dead relative link in living docs (`supersede.py --check`); hook clean for docs | `git revert` per batch |
| **3. scripts/ forward rule** | create `scripts/oneoff/` + README; client or WA CLAUDE.md rule text | 30 min | no | yes | | revert |
| **4. Merge** | 5.2 steps 1-14 | 3 h | **yes**: creates the GitHub repo, or OKs `gh repo create` | **no Pioneer session at all, Excel closed** | tree identity (step 7), commit counts, `git status` clean, LFS fsck, a push that others can clone | 5.3 |
| **5. Fix-ups** | `Stage-PowerQuery.ps1`, skill move + correction, client CLAUDE.md and dedup of the 3 CLAUDE.md files, memory (5.5), Timesheets wording, Claude-Tooling mirror, TASKS.md scaffold item, the 4.4 small fixes | 2-3 h | reviews the CLAUDE.md dedup | yes, after Phase 4 | `Stage-PowerQuery.ps1` dry run; the skill appears in a fresh session's list; hook clean | revert per commit |
| **6. Retire old repos** | `MOVED.md` in each, archive on GitHub; delete `C:\pioneer-merge\backup\` | 20 min | **yes** (archiving a repo is the user's call) | yes | old repos read-only | un-archive (GitHub allows it) |
| **7. Optional, workspace level** | the 4 AFDS files at `claude/` root (open question 6); stale autoMode "trusted repo" text in `settings.json`; a later batch move of `ran` one-offs to `scripts/oneoff/` | 1-2 h | yes for AFDS and settings | yes | hook clean at root | move back |

Total: about **13-16 h**, of which about 3 h needs the quiet window.

The order is deliberate. **The hook comes first**, in report-only mode, so it measures the before-state, and every later phase
has a check that says "done". **Doc moves come before the merge** so the merge commit carries a clean tree,
and the 4.2 table's link rewrite runs in a repo layout that isn't changing under it.

---

## 8. Open questions (real decisions only)

| # | Question | Recommendation |
|---|---|---|
| 1 | **Client-level repo (`pioneer-transformer`, option B) or fold into Workflow-Automation (option A)?** Either way, this reverses the rule recorded on 08-17 ("push scoped to a single project, never one repo per client"). | **B.** For Pioneer the three projects are one system: they share the `Index`, the viewer, the mirror, and cross-read each other's files. Keep one-repo-per-project as the default for future clients whose projects don't share a system. |
| 2 | **Billing after the merge:** does new work on the FRM10-12 or FRM09 workbooks keep billing to those buckets, or does all Pioneer work go to Workflow-Automation? | **Keep the buckets and bill by what the work is for** (as FRM11 does without a repo). Past rows are untouched either way. |
| 3 | **Build-night boards:** make `Clients/Pioneer Transformer/build-nights/` the single tracked copy and delete `Workflow-Automation/docs/build-nights/` (after merging their few unique lines)? | **Yes.** It removes the two-copies rule and the manual harvest. |
| 4 | **Doc placement:** OK to archive the 4 self-declared superseded docs now, and do you confirm the "likely" ones (HANDOVER-2026-09-11, demo cheat sheet + PDF, visual companion) and the 4 plans marked \* as done? Also OK to replace dated `checklist-<date>.md` with one living `docs/CHECKLIST.md`? | **Yes to all four self-declared.** Confirm the rest item by item. **Yes to `CHECKLIST.md`**, following the `CUTOVER-RUNBOOK.md` precedent. |
| 5 | **Existing one-off scripts:** index them in place (forward-only `oneoff/`), or also move the ~60 existing one-offs now? | **Index in place now.** Move them in one later batch once each is marked `ran`. That avoids 146 link edits and 26 import fixes while another session is active in `scripts/`. |
| 6 | **The AFDS files at the workspace root** (`Add-JiraWorklogs.ps1`, 2 html): where do they belong? | `Clients/AFDS/` if AFDS is a client you bill, otherwise `Timesheets/tools/`. Either way they get into a repo. |
| 7 | **GitHub actions:** should I create the new repo and archive the old ones with `gh` (logged in as `sankerbaril-biplan`, `repo` scope), or will you do it on github.com? Also check the org's LFS quota (adds about 185 MB while the old repos keep theirs). | **I run `gh repo create` after your explicit go-ahead in Phase 4. You archive in Phase 6.** |
