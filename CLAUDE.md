# Workflow-Automation — Pioneer Transformer

## What this is
A cross-cutting home for Pioneer Transformer's automation/workflow-logistics initiative —
the parts that span beyond any single workbook (FRM09, FRM10-12): SharePoint list design,
Power Apps/Power Automate flows, and the overall data-flow architecture connecting them.

It does not replace FRM09 or FRM10-12 as staging copies of specific workbooks — see
[[workspace-repo-structure]] for that convention. This repo is where the *shape of the whole
system* gets documented and planned, plus schema/config for new SharePoint lists before
they're built live.

## Why this repo exists
FRM10-12 is mid-migration: some of its data already lives in SharePoint lists (`Order`,
`Models`, `Model Revisions`, `Models SA`, `Clients`, ...), pulled back into the Excel
workbook via Power Query. The next piece is the per-unit production layer — today
`TableOrders.pq` expands each order into individual job rows (`"21865-1/5"` format) purely
inside Power Query, and staff hand-update production-tracking fields (Location, Status,
Tank, Frame, Core Status, Coil Winder, Tanking/Delivery Date, BO) directly in the live Excel
file. Moving that layer into its own SharePoint list (**Order Items**) is the next migration
step, and it needs the same kind of careful, staged design FRM10-12's list migrations have
had — hence a dedicated place to plan it before touching production.

## Folder layout
- `docs/roadmap.md` — **start here**: ties the other docs together into one picture of
  what's planned and in what order.
- `docs/` — the description document (`infrastructure-overview.md`), the build plans
  (`order-items-build-plan.md`, `phase1-plan.md`), and other planning notes.
- `docs/diagrams/` — exported diagram images/source files (the Mermaid diagrams embedded in
  `infrastructure-overview.md` are the primary/current copy; export here if a tool needs a
  static image).
- `workflow-data/` — exports/samples of workflow data (Power Automate flow definitions,
  run logs, etc.) once that automation layer exists.
- `workbooks/` — copies of workbooks that are analysed here but belong to no repo of their own
  (currently FRM11).
- `power-query/<workbook>/*.pq` — the M code of those workbooks, one file per query, first line
  a `// Query: <real name>` comment so the filename is not load-bearing. **Read these instead of
  reopening the workbook.**
- `scripts/` — analysis and generation scripts. Two conventions worth knowing:
  - **`Export-PowerQuery.ps1`** pulls every query out of a workbook into `.pq` files. It is the
    counterpart to `FRM10-12/scripts/Sync-PowerQuery.ps1`, which pushes them back in; same Excel
    COM surface (`$wb.Queries` → `.Name` / `.Formula`), so the two round-trip. It opens
    `ReadOnly`, never saves and **never refreshes** — do not relax that, a generic refresh on
    FRM10-12 wipes its native formula columns.
  - The `gen_*.py` / `*_scan.py` scripts all read the newest `sharepoint-lists/*.csv` export
    through `load_exports.py`, which already handles the `ListSchema` record described below.
    Reach for one of these before hand-rolling a parser.
- `sharepoint-lists/` — canonical export staging for **all** shared SharePoint lists used
  across Pioneer Transformer projects (`Models`, `Model Revisions`, `Models SA`, `Order`,
  `EngineeringChangeOrders`, `ModelChanges`, `Clients`, plus new-in-design lists like
  **Order Items**). FRM10-12 stopped keeping its own duplicate copies of these (2026-08-17)
  and points here instead — this is the one place to look for current list-shape exports.
  Filenames follow `{List Name} {YYYY-MM-DD} {HHMM}.csv` (export timestamp appended, not
  just the list name) — added 2026-08-13 so re-exports don't silently overwrite the record
  of when a snapshot was taken, which matters while the manual `Order Items` build is still
  in progress. Superseded exports move to `sharepoint-lists/Archive/` rather than being
  deleted. Docs reference this folder generically (`sharepoint-lists/*.csv`), not by exact
  filename, so this convention can keep evolving without breaking doc links.

  ⚠️ **Two things about these exports that will silently give you wrong answers** (learned
  2026-09-05, after an analysis returned "0 differences" from a file that had been parsed as its
  own schema):
  1. A SharePoint *Export to CSV* writes a single enormous `ListSchema={...}` **record first**, then
     the real header row. Skip the first *record* (not the first line — the schema contains
     newlines) or a CSV reader takes the schema as your column names.
  2. **Lookup columns do not serialise.** `Order Items.Model`, `.Model Revision` and `.Order Number`
     come back blank — 2 to 4 populated out of 1052. The `_TextField` mirrors carry the real values
     (986/1052). Use those for any analysis, and remember they are only as fresh as the last
     TextField sync run.

  The export also follows **the currently selected view**, not the list. The first Order Items
  export of 2026-09-05 was the BO Tracking view — 3 rows, 23 columns — and looked like a real
  export until counted. Switch to All Items first, and sanity-check the row count.

## Related repos
- `../FRM09/` — Winding department workbook; depends on FRM10-12's `TableOrders` via its own
  Power Query, not on this repo's list exports directly.
- `../FRM10-12/` — the main planning/production workbook and source of truth; most of the
  underlying Power Query/SharePoint migration work happens there, and its `.pq` queries hit
  live SharePoint directly (never stale). This repo documents the system FRM10-12 is part of,
  stages the next list to migrate into it, and now holds the canonical shared-list export
  snapshots FRM10-12 used to duplicate (see `sharepoint-lists/` above).
- **FRM13** (`PRO1.FRM13 - Desplan - Auto.xlsx`) — the Engineering/drawing tracker, live at
  `Pioneer Planification/General/FAB/Suivi/Dessin`, with a working copy at
  `../FRM10-12/linked-workbooks/`. It has **no repo of its own**, but it is a real upstream
  dependency of this project, discovered 2026-09-05:
  - Its `LeedTime` table (sheet `DelaisApproParClients`, `A6:H24`) is the **only** source of
    client lead times — 17 clients plus a `GENERIC VALUE` row of **26 SEM (weeks)**, along with
    the critical part and supplier driving each one. FRM10-12 queries it in as
    `ClientLeadTimes`, and branch 7 of the Estimated Delivery formula depends on it.
  - ⚠️ **`Order.Lead Time` is NOT this value.** Measured 2026-09-05: of the 342 orders whose
    client appears in `LeedTime`, **306 disagree and 36 agree** — it is mostly the SharePoint
    column default (26) with occasional hand edits, i.e. a per-order override. HYDRO QUEBEC
    should be 28 weeks; 144 of its orders say 26 and 84 say 20. Do not feed it into branch 7.
  - The Excel formula's `XLOOKUP(..., default 52)` also contradicts FRM13's own generic value
    of 26. Whichever way that is settled, settle it in both places.
  - It also carries its own `TableOrders` (per order, `B7:AN169`) — same name as FRM10-12's but
    a different table with different columns. Don't conflate them.
- **FRM11** — the **tank tracking form**, and the owner of the tank/paint supplier statuses.
  No repo of its own; discovered 2026-09-05 from the user and confirmed against
  `FRM10-12/linked-workbooks/Archive active.xlsx`, which carries `TableArchiveFRM11`
  (4,052 rows × 39 columns) on an `Archive FRM11` sheet with its own Power Query.
  - It tracks each tank through **two outside suppliers** — fabricator (`Fournisseur CUVE`:
    CADORETTE, METELEC, FRAMECO, FALCON…) then paint (`RAD` / `B-WALL`) — and back to Pioneer,
    with **supplier reports attached**. `Tank Supplier Status` / `Paint Supplier Status` and
    `Code cuve` / `Code peinture` are the live columns; FRM10-12's `List` sheet holds only the
    vocabularies for its own dropdowns.
  - **Keyed on `NUMÉRO DE CUVE`, which is the unit ID** (`21535-1/2`). ⚠️ `Order Items.Tank` is
    **not** a tank number and is not the join key.
  - 🔴 **It reads FRM10-12 as its root data source** — analysed 2026-09-06 from the workbook
    itself; M code tracked at `power-query/FRM11/*.pq`, full write-up in
    `docs/frm11-coupling-analysis-2026-09-06.md`. This is a **hard dependency**, not a sync:
    - `TableOrders` → `Imported FRM10_12 Data` (**10 columns**, referenced by literal string:
      `Order`, `Client`, `Type`, `KVA and KV`, `PO Item #`, `Location`, `Tanking Date`,
      `Original Tanking Date`, `Tanking date change justification`, `Tank`) → `FournTank`
      → **890 live rows** → **8 supplier report sheets** → 8 outside companies.
    - It also imports `TableCuveCodes` / `TablePeintureCodes` / `TablePioneerCodes` from
      FRM10-12, so the tank-status vocabularies cannot drift between the two.
    - Its purge rule reads FRM10-12's `Location` and `Status` **in two-letter codes**
      (`{XT,TE,FI,LI}`, or `TA` + `Status` containing `TE`) — the transfer flow converts those to
      display names on the way into SharePoint, so a SharePoint-native source must translate back.
    - **Action: do not reshape or retire `TableOrders` as part of this migration.** Both consumers
      can coexist; the risk is a later cleanup pass deciding the workbook is redundant.
  - 🔑 **Every external workbook is resolved through a SharePoint list named `Index`**
    (`Title` → `Path`) on `https://ermcopower.sharepoint.com/sites/PioneerPlanificatio`, via an
    `ImportFromIndex(sheet, table)` helper. That indirection is why the 2026-09-04 move of
    FRM10-12 to `Revue/Formulaires/` did not break FRM11 — **and it makes the eventual cutover a
    one-row edit**: publish a SharePoint-sourced workbook exposing `TableOrders`, repoint the row,
    no M changes. Assume other workbooks use the same helper.
  - `In FRM10_12` and `Last Synchronisation Date` live on **`TableArchiveFRM11`** in
    `Archive active.xlsx`, not on FRM11's live table.
  - **Out of scope for the Order Items migration** — supplier state is a different axis from the
    unit's own production progress. See `docs/infrastructure-overview.md`.
### 🔑 How every Pioneer workbook finds every other one

Mapped 2026-09-06 from the M code of all five workbooks — **98 queries**, tracked under
`power-query/<workbook>/*.pq`, full write-up in `docs/workbook-data-graph-2026-09-06.md`.

**There is not one hardcoded workbook URL in the entire estate.** Every cross-workbook read goes
through a SharePoint list named **`Index`** (`Title` → `Path`) on
`https://ermcopower.sharepoint.com/sites/PioneerPlanificatio`, via an `ImportFromIndex(title, table)`
helper copied into each file. Consequences:

- Moving a workbook breaks nothing if its `Index` row is repointed — that is why the 2026-09-04
  move of FRM10-12 was survivable.
- **The eventual FRM10-12 cutover is a one-row edit**, not a rewrite: publish a SharePoint-sourced
  workbook exposing `TableOrders`, repoint the row, and FRM09 / FRM11 / FRM13 follow unchanged.
- `Index` is unversioned and unwatched. Treat it as production infrastructure.

Who reads what:

| `Index` title | Read by | Tables |
|---|---|---|
| **FRM10-12** | FRM09, FRM11, FRM13 | `TableOrders` (all three), plus FRM11 also takes `TableCuveCodes` / `TablePeintureCodes` / `TablePioneerCodes` |
| **FRM11** | FRM13 | `TableFournTank` |
| **FRM13-Auto** | FRM10-12 | `LeedTime` |
| **Archive active** | FRM10-12, FRM11, FRM13 | the `TableArchive*` tables |
| **BO Manager** | FRM10-12 | `TableBO` |
| **Temps Standard** | FRM10-12 | `TableJobTimes` |
| **Rapport …** × 8 | FRM11 | `TableReport` (title computed at runtime) |

🔴 **There is a cycle:** FRM10-12 → FRM13 → FRM10-12 (and the longer FRM10-12 → FRM11 → FRM13 →
FRM10-12). No refresh order makes the estate consistent, and it is the likely cause of
`Order.Lead Time` disagreeing with FRM13's `LeedTime` on 306 of 342 rows.

🟢 **FRM10-12 already reads the SharePoint lists directly** — `Orders`, `Models`, `Model Revisions`,
`Models SA` via `SharePoint.Tables`, with `FlattenSharePointLookupLists` (expands lookups) and
`ApplyColumnMap` / `ColumnMap` (declarative rename/retype). The machinery a SharePoint-sourced
`TableOrders` would need is already in production.

⚠️ **And that is why `Refresh All` destroys FRM10-12:** `TableOrders` reads the sheet table it
writes back to, and its second step strips six native formula columns (`Estimated Delivery Date`,
`Price CAD`/`USD`/`Price`, `Navigation Order`, `Navigation Model`). A generic refresh re-lands the
table without them. Office Script button only.

- These are separate git repos — the cross-links above are documentation only (relative
  folder paths under the same client directory), not a git/build dependency.

## Working notes
- Binary Office files here are tracked via **Git LFS** — see `.gitattributes`.
- This repo has no live workbook of its own — nothing here should be treated as a source of
  truth until it's actually built in SharePoint/Power Apps and confirmed against FRM10-12.
