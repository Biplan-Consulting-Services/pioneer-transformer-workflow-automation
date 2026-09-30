> **Living document.** The organisation plan for Pioneer Transformer, approved by the user 2026-09-29.
> Status (2026-09-29 evening): phase 1 (model + Punch List epics) done; phase 2 (timesheet epics, local Shift
> Console, Jira push workflow) done; phase 3 (repo merge) built and verified in staging, swap in progress. Decided
> the same evening: workbook registry + `wb` tool, Power Query `_shared/` + `pq` tool, and the **work system**
> (task files in the repo replace the Punch List as master; see "Work system"). Update this file in place,
> never create a dated copy. It supersedes `workspace-cleanup-plan-2026-09-29.md` (kept as a record for its merge mechanics).

# Pioneer Transformer: reorganise the work around client → project → epic → task

## Context

The first cleanup plan (`Workflow-Automation/docs/workspace-cleanup-plan-2026-09-29.md`) was a *file-tidying* plan. It
merged three repos and sorted 77 docs into folders. The user's answers (2026-09-29 17:37) ask for more than that: an
organisation of the **work itself** that makes their own workflow more efficient:

1. **One client-level repo, with no workbook-shaped folders.** FRM10-12 / FRM09 / FRM11 / FRM13 are systems being
   phased out, and any piece of work can touch several of them. So work shouldn't be filed by workbook.
2. **Billing is per project**, and "Workflow-Automation" is really a project made of several big sections, i.e. **epics**.
3. **Build nights** repeat the overall project. They are short-term objectives inside the larger story, not a
   second tracking system.
4. **Stop producing a new doc every time something is done.** Consolidate knowledge into a stable structure.
5. **Scripts:** find a reusable way to write them, without slowing quick fixes down.

The research this session (3 read-only agents) measured the current state:
- 107 timesheet rows in 10 natural themes
- a 1,142-line roadmap with 5 workstreams plus about 45 numbered items
- 11 docs about the archive alone
- 3 build-night boards copied by hand into the repo
- a db-backed Punch List (109 items, 12 groups)
- **AFDS = the project key in the Biplan Consulting Jira** (`biplan-consulting.atlassian.net`), where Pioneer
  Transformer hours are billed as worklogs against 12+ tickets (`Add-JiraWorklogs.ps1`, `jira-worklog-plan.html`)

## Model (decided with the user 2026-09-29)

```
Client      Pioneer Transformer                    (billing client, unchanged)
Project     Workflow Automation  ~ Jira AFDS       (billing project: one timesheet CSV)
Epic        10 areas (below, adjustable later)     (one living page each)
Task        PT-### task file in the repo (MASTER)   (epic, status, sprint, owner, jira = AFDS-###)  [was: Punch List item]
Sprint      S-<date> build night / S-<yyyy>-W<nn> week (a tag on tasks + a generated report, not a board)
Work log    timesheet row, tagged with epic (+ task) (Shift Console; pushed to Jira as worklogs)
```

**Jira relationship (decided): the task files are the master and Jira mirrors them** (2026-09-29 evening: task files
replace the Punch List as master, see "Work system").
- A task may carry its AFDS ticket number; a timesheet row carrying a task ID then finds its Jira ticket through it.
- Timesheet hours are pushed to Jira as worklogs through a generalised `Add-JiraWorklogs.ps1`. It stops being a
  one-off with hard-coded entries and reads the timesheet CSV plus the item → ticket map, with a dry run and the
  existing 40 h/week check.
- Jira stays the billing record. Nothing is created in Jira automatically until the user approves each push.

**Candidate epics.** Taken from the roadmap workstreams, the Punch List groups and the timesheet themes:

**The epics in use (12, tagged on all 109 Punch List items 2026-09-29; item counts at tagging).** Two were added
while tagging because items fitted none of the original 10: *Workflow tasks (Phase 1)*, a roadmap workstream, and
*Workspace & tooling*, this reorganisation itself.

| Key (Punch List `epic`) | Epic | Absorbs | Items |
|---|---|---|---|
| `order-items-sync` | Order Items & parent sync | N2/N3 flows, trigger flow, lookups, mirrors | 19 |
| `nightly-sync-archive` | Nightly Sync & archive | ns, ar, Archive active, the 11 archive docs | 24 |
| `data-quality` | Data quality | data-fixes, staff questions, choice vocabulary, `_TextField` backfill, models dedup | 25 |
| `mirror-health` | Mirror & health | SharePoint mirror, journal, health checks, rollback | 9 |
| `power-app` | Power App | pa, app save logic, export | 8 |
| `workbook-phaseout` | Workbook phase-out | FRM10-12 / FRM09 / FRM11 / FRM13 / BO Manager / Index | 4 |
| `reporting-kpis` | Reporting & KPIs | OTD / Duke RFP, Power BI, Estimated Delivery Date logic, FX | 3 |
| `monday` | monday.com | mon | 6 |
| `engineering-docs` | Engineering document control | ed | 6 |
| `workflow-tasks` | Workflow tasks (Phase 1) | order entry → planning → client dates, design backlog | 2 |
| `staff-enablement` | Staff enablement | handbooks, views guides, training, change requests | 2 |
| `workspace-tooling` | Workspace & tooling | this organisation plan, repo merge, tools, hooks | 1 |

## Repo and folder shape

- **One repo at `Clients/Pioneer Transformer/`.** Workflow-Automation, FRM10-12 and FRM09 are merged with their
  full history (`_reorg/reorg.py`: each repo's history rewritten under a prefix with `git filter-branch`, then a plain
  merge and one `git mv` commit, so `git log --follow` reaches the first commits). Runbook: `_reorg/SWAP.md`.
- **Corrected 2026-09-29 (user):** the FRM10-12 repo's `viewer/` **is** the live FRM10-12 (deployed 09-11 at
  `Revue/FRM10-12.xlsx`; staff just call it FRM10-12). The repo's top-level `workbook/`, `power-query/`, `scripts/` are
  the old hand-maintained FRM10-12, frozen since the cutover. In the new layout the live set is plain "FRM10-12" and
  the word "viewer" disappears; the old set is "FRM10-12 pre-cutover".
- **Workbooks (decided 2026-09-29):** `workbooks/registry.csv` (one row per workbook: name, status live/pre-cutover/
  retired, SharePoint location + `Index` title, who reads it, queries folder, epics) + one folder per workbook
  (`workbooks/<Name>/<Name>.xlsx` working copy + `snapshots/`) + `tools/wb.py` (`wb snapshot|latest|list`), which
  replaces `stamp_exports.py`, `tidy_snapshots.py` and every filename glob in the scripts.
- **Power Query (decided 2026-09-29, level A):** `power-query/_shared/` holds the one copy of every query used by
  more than one workbook (ColumnMap, ValueConversions, FlattenSharePointLookupLists, ImportFromIndex, the date fix);
  `power-query/<Workbook>/` holds only that workbook's own queries plus the list of shared ones it uses. One `pq` tool
  (`export`, `diff` = drift between a file and the repo, `build`, `push` into a working copy / paste sheet) replaces
  `Export-PowerQuery`, both `Sync-PowerQuery`, `Stage-PowerQuery`, the copy checker and `pq_graph`. Later, not soon:
  update ColumnMap automatically when the mirror's columns change. Level B (a Power BI dataflow as the one cleaned
  data source) is a separate spike, only after licensing and Excel-consumption checks.
- **Two halves, revised after the user's feedback (2026-09-29):**
  - **Data is organised by the *type* of artifact, at the client level, shared.** A workbook, a flow or an Office
    Script belongs to no single project or epic: it can serve several.
  - **The work** (projects, epics, sprints) lives separately and *points to* the data. It never holds copies of it.

```
Clients/Pioneer Transformer/                  one repo
  CLAUDE.md  CATALOG.md                       rules; asset <-> project/epic index (generated, see below)
  ── DATA, by type (shared) ─────────────────────────────────────────────────────────
  workbooks/<Workbook>/                       current copy + Archive/ (dated copies), one folder per workbook:
                                                FRM10-12 (incl. the viewer), FRM09, FRM11, FRM13, Archive active,
                                                BO Manager, BO Report, SharePoint mirror.xlsx ...
  power-query/<Workbook>/*.pq                 M code per workbook (the WA export + FRM10-12's own, reconciled)
  office-scripts/<Workbook>/                  Office Scripts per workbook
  flows/<Flow name>/                          version history (flow_version: history.json, _inbox, _outbox)
  sharepoint-lists/                           exports, mirror/, schema, formatting, views
  power-apps/                                 app exports (pa-export)
  artifacts/                                  published page sources (punch list, trackers)
  rollback/                                   before-values of every list write
  tools/                                      reusable scripts + libs (sp.js, flowlib.py, mirror_lib, flow_version…)
  ── WORK ───────────────────────────────────────────────────────────────────────────
  projects/workflow-automation/
    README.md                                 the project: goal, epics, where we are (= CHECKLIST)
    epics/<epic>/README.md, decisions.md      living knowledge + dated decision log
    epics/<epic>/records/                     frozen evidence (reviews, paste sheets, audits)
    epics/<epic>/scripts/                     one-off fixes for that epic (STATUS: header)
  projects/<next project>/ ...                a future project (e.g. the Duke/Power BI reporting, if billed separately)
  sprints/<date>.md                           build-night / weekly objective logs
  requests/                                   incoming client requests (e.g. Duke OTD) and their deliverables
```

- **Many-to-many without copies.** Each artifact folder gets a small `ASSET.md` (or a front-matter block for a
  single file) listing the projects and epics it serves. Example: `workbooks/FRM10-12/ASSET.md` →
  `epics: order-items-sync, nightly-sync-archive, workbook-phase-out, reporting`. `CATALOG.md` is generated from
  these files by `tools/catalog.py`, in both directions (asset → epics, epic → assets). Each epic README embeds its
  own list, so a workbook used by 4 epics appears in all 4 without being duplicated. The hygiene hook flags an asset
  that serves nothing or an epic that references a missing asset.
- **Documents:** knowledge goes into the epic's README and `decisions.md`, not into a new dated doc.
  - A dated doc is written only as evidence (`records/`), never as the current state.
  - The Punch List replaces the roadmap's task tables and the dated checklists.

## Nothing is lost: the guarantee (applies to every move phase)

1. **Inventory before anything moves.** `tools/inventory.py` lists every file in the 3 repos, the client-level loose
   files and the root AFDS files, including untracked and ignored files, and `.git` LFS objects. For each file:
   path, size, sha256, LFS pointer, and git status. It's committed as `_reorg/inventory-before.csv`.
2. **An explicit move map.** `_reorg/move-map.csv` gives old path → new path for **every** file in the inventory,
   with no gaps (the script refuses if any file has no destination). You review it before execution.
3. **Moves only, never deletes.**
   - Moves use `git mv` (history kept; `--follow` works).
   - Duplicates are merged **only when they are byte-identical**. For example, 21 of the 23 FRM10-12 `.pq` files are
     identical in both repos. The 2 that differ (`ColumnMap.pq`, `TableOrders.pq`) are **both kept**, with a
     `.from-<repo>` suffix, until you decide.
   - Superseded docs go to `archive/`. They're not deleted.
4. **An after-check.** `tools/inventory.py --verify` re-hashes the new tree. Every sha256 from the "before" list must
   be present at its mapped path, and the total file and byte counts must match (minus exact duplicates, which are
   listed). Any difference stops the phase before the commit.
5. **Links are rewritten from the move map**, then checked: no doc or script points to an old path. The refresh
   script, the hooks, the skills, `Sync-PowerQuery.ps1` and the memory notes are updated from the same map.
6. **Rollback:** each phase is a single commit on a branch, and the old `.git` folders are kept until the new
   structure has run for a week.

## Work system: tasks, sprints, reports (decided 2026-09-29 evening, replaces "Build nights → sprints")

**The problem.** One task's state was written in up to six places (Punch List, `roadmap.md`, the dated checklist, the
build-night board, `session-tracks.json`, `STATUS.md`); each night or day copied it into a new document, the copies
drifted, and references were prose. **The fix is not to sync documents but to stop copying state:** one store, and
everything else either points into it by ID or is generated from it.

1. **One store, in the repo.** `projects/workflow-automation/tasks/PT-###.md`, one file per task, front matter
   `id, title, epic, status, sprint, owner, jira, blocked-by` + notes, links, what "done" means. Beside it an
   append-only `journal/<yyyy-mm>.jsonl` (`ts, session, task, text`) that parallel sessions only ever add lines to.
2. **Naming protocol.** Tasks `PT-###` (sequential per project; the epic is a field, so moving a task between epics
   breaks nothing). Sprints `S-2026-09-24` (build night) / `S-2026-W40` (week). Decisions `D-###`, anchored in each
   epic's `decisions.md`. Any doc just writes the ID; a hook flags unknown IDs and done tasks still in an open sprint.
3. **Views, not documents.** A local page like the Shift Console (`index.html` + hook-built `data.js`, refreshed every
   minute), possibly the same shell with a Tasks tab: **Board** (epic × status), **Sprint** (tonight's tasks, who
   holds which, the live journal), **Next** (replaces the dated checklist: CLAUDE.md says "start from Next").
4. **Reports are generated and archived.** Closing a sprint writes `sprints/S-<id>.md` (planned tasks, final status,
   journal entries): frozen, never hand-edited, the build-night progress archive. Facts learned go into the epic's
   README/`decisions.md` by ID, not into the report. The old hand-written boards stay in `sprints/` as history.
5. **A small CLI for sessions:** `work start PT-112 --session <name>`, `work log PT-112 "…"`, `work done PT-112`,
   `work report S-…`, `work next`. Hooks rebuild the page's data.
6. **Billing link:** a timesheet row can carry `PT-###`; the task carries `jira`, so the Jira push finds its ticket
   through the task (this removes the manual `jira/ticket-map.csv` / `overrides.csv` step for new rows).

**Master: repo files (user, 2026-09-29).** Git history of every status change, checkable references, works offline,
kept current by hooks. The Punch List's 109 items are migrated once to `PT-` files; the Punch List is then retired
or kept as a read-only published copy for the phone. Status changes go through Claude or an editor (the local page
cannot write files).

## Scripts

The scripts research found that the same safety pieces are rewritten in every console script (36 x/n scripts):

| Piece | Rewritten in |
|---|---|
| `J()` fetch helper | 34 |
| `page()` | 19 |
| digest call | 23 |
| MERGE writes | 22 |
| zero-row abort | 26 |
| read-back | 25 |
| UNDO block | 15 |
| backoff | 9 |

Only `x27_restore.js` is reusable. On the Python side, the flow-authoring helpers (`unwrap`, `find`, `flatten`,
`newest_live`) are redefined in about 5 `apply_*` files, and only 3 import them from `apply_v007_connref_statusdate.py`.

- **`tools/sp.js`: one console runtime.**
  - `get`/`page` with backoff, `digest`
  - `update(list, id, formValues)` via `ValidateUpdateListItem`, the proven method from
    `memory/sharepoint-writes-via-chrome.md`; `recycle(id)` for deletes
  - `CONC` workers
  - `plan → dry run → apply`, where apply is refused unless `APPLY` is true
  - automatic before-values that become the rollback: downloaded as a file in the browser, or saved by Claude
    when it runs the script through claude-in-chrome
  - zero-row abort and read-back verification built in
- **A quick fix stays quick.** A short recipe declares only `list`, `select`, `filter` and `change(row)`, then calls
  `run(recipe)`. It lives in `epics/<epic>/scripts/<date>-<task>.js` with a `STATUS:` header
  (draft / ran / superseded). The safety comes from the runtime and is never copied into each script.
- **`tools/flowlib.py`** gathers `unwrap`/`find`/`flatten`/`newest_live`/the connection-reference checks/the
  exact-diff assert, and the `apply_*` scripts import it. **`tools/gen.py`** holds a single templating helper for the
  generators (`__NAME__` placeholders plus the GENERATED banner).
- **Reusable tools move into `tools/` once**: mirror, flow_version, x27_restore, check_*, the libraries. Existing
  one-offs stay where they are and get indexed, then move in a batch after they're marked `ran`.
- **Immediate safety fix:** `x2_set_delivered.js` is committed with `APPLY = true`. Reset it to `false`.

## Answers to the other points

- **Q6, AFDS:** see Context. It is the Jira project where Pioneer hours are billed. The 3 root files are Pioneer
  billing tools and belong under the client, in the timesheet tooling area.
- **Q7, GitHub:** a step-by-step guide at that phase. I run `gh repo create` after your go-ahead, and you archive
  the 3 old repos and check the LFS quota.
- **Q8:** noted. Manual edits are the staff's responsibility, so there is no follow-up.
- **Q9, parent `_TextField` mirrors: a flow is better. I agree with you.** Staff edit directly in SharePoint (all
  410 Status Date edits and this morning's 614-row cleanup were grid edits), so an app-only fix would miss them.
  Add a guarded "update parent mirrors" action to each parent's existing N3 flow. It writes only when the mirror
  differs from the lookup's value, so the second run it causes finds nothing to do and stops. It needs the
  `needsUpdate` guard extended to cover the mirrors, and the Models ↔ Model Revisions pair checked for a cycle
  (`docs/roadmap.md:922-966`, `infrastructure-overview.md:587-590`). Backfill after the flows are in place: a
  console script with a dry run, run with the N3 flows off or accepting the burst.
- **Q10, choice values (clarified).** A Choice column has a fixed list of allowed values. SharePoint still holds
  values outside that list: they were imported from Excel or written by a flow before the list was set.
  - Example, Model Revisions → **Model Type**: the allowed values are `3PH PAD (PADMOUNT)`, `1PH SUBMERSIBLE`,
    `3PH SUBMERSIBLE`, … but 33 rows say `PADMOUNT` and 25 say `SUBMERSIBLE`.
  - The consequences are concrete: a view or Power App filter on "3PH PAD (PADMOUNT)" misses those 33 models, the
    edit form shows the field as blank or invalid, and the Order Items copies (`RevModelType`, 750 rows) carry the
    same problem.
  - For **each distinct wrong value** there are three possible decisions:
    - **Map:** it means an existing choice, so rewrite it. `PADMOUNT` → `3PH PAD (PADMOUNT)`, `N` → `No`,
      `LUMINOL` → `Luminol`.
    - **Add:** it is a legitimate value that is missing from the list, so add it to the choices (e.g. `MIDEL` in
      Oil Type if that oil is really used).
    - **Wrong column / garbage:** clear it or move it. `C2`/`POWER-W` in Model Type are Description values;
      `46452` in TrimestrialCustomer is an Excel date number.
  - **The workflow:**
    1. I generate a review workbook, one sheet per column, with the columns: current value · count · example rows ·
       proposed decision · target value.
    2. You (or the right staff member) fill in the decision column.
    3. One `tools/sp.js` recipe applies it, with a dry run and a rollback file.
    4. Only the **parents** are fixed. The N3 sync then corrects the Order Items copies on its own. Expect a burst of
       N3 runs.
  - Built when the Data quality epic starts.

## Phases (each small, reversible, approved one by one)

1. **Model (start here, decided).**
   - Add `epic`, `sprint` and `jira` fields to the Punch List items via ArtifactData batch writes: 109 docs, 3
     batches of ≤50, each pinned with `if_version`. Tag every item: the mapping comes from its current `group`, and
     the `data-fixes` / `parked` / `p` items get individual calls.
   - Add an epic filter to `artifacts/punch-list.html`. That's a layout change, so it's the one allowed republish,
     to the same URL (the data lives in the db, so it isn't affected).
   - Save the epic list and its definitions in the client-level CLAUDE.md, plus a memory note.
2. **Timesheets + Jira.**
   - Add an `epic` column to the Workflow Automation CSV. Edit in place: replace the header plus append, never a
     DictWriter rewrite (memory `feedback_timesheet_csv_edit_in_place`). Update the timesheet-logging skill so each
     new row is stamped with an epic.
   - Add a third Shift Console filter level. That changes `shift-console.html`'s behaviour, so it's done with the
     user's OK, following its "patch, never rebuild" rule.
   - The FRM10-12/FRM09/FRM11 buckets stay for past rows. New work logs to Workflow Automation with an epic, and
     `Workbook phase-out` covers the workbook work.
   - Generalise `Add-JiraWorklogs.ps1`: it reads the CSV plus the item → AFDS map, with a dry run by default. Move it
     under the client's timesheet tooling, along with the 2 AFDS html files.
3. **Repo merge + reorganisation by type.**
   - Inventory, then the move map, which you review.
   - The history merge with `filter-repo`, as in the first plan.
   - `git mv` into the type folders, then the after-check (see "Nothing is lost").
   - Link rewrites.
   - No other session running, and Excel/PowerPoint closed.
   - Then write the `ASSET.md` files and generate `CATALOG.md`.
   - **Revised 2026-09-29 evening, in this order:** (a) the swap, with the corrected FRM10-12, the workbook registry +
     `wb`, and the `power-query/_shared/` layout; (b) the `pq` tool; (c) the work system (task files, journal,
     viewer, CLI, Punch List migration). After (c), no more hand-written build-night boards or dated checklists.
   - Duplicates rule, refined with the user: **one clean copy of each thing in the tree.** A copy that differs only
     because it's older (a hand copy of a build-night board, a superseded query export) is not kept as a second
     file; it stays retrievable in the merged git history, and the after-check confirms it is there.
4. **Epic READMEs:** consolidate the existing docs into the 12 living pages and move the rest to `records/` or `archive/`.
5. **Tools:** extract `tools/sp` from the x## scripts and add a quick-fix template.
6. **Keep-clean:** the session-start hygiene hook, the supersede helper, the CLAUDE.md "where things go" rules.

**Housekeeping in phase 1:**
- This plan goes into the repo as `docs/organisation-plan.md`, undated because it's a living document. The first
  plan (`workspace-cleanup-plan-2026-09-29.md`) gets a "superseded by" header and stays as a record; its merge
  mechanics (sections 5 and 7) are referenced, not copied.
- The Punch List item `ws-cleanup-plan` points to the new plan.
- The N3 retry (`scripts/apply_n3_retry.py`, ready) waits for the user's 4 exports, after this plan per the user.

## Verification

- **Model:** every Punch List item has an epic, and the page's filter by epic works.
- **Merge:** the tree-hash comparison shows old and new are byte-identical, `git log --follow` works on moved files,
  and the tests pass (`test_mirror_tools.py`, `test_mirror_health_state.py`, the rest of `test_*`).
- **Mirror refresh:** runs from the new path.
- **Timesheets:** the Shift Console shows the same totals before and after.
- **Docs:** nothing links to a moved file (link check in the hygiene hook).
