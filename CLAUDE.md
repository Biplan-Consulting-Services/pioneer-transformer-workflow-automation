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
- These are separate git repos — the cross-links above are documentation only (relative
  folder paths under the same client directory), not a git/build dependency.

## Working notes
- Binary Office files here are tracked via **Git LFS** — see `.gitattributes`.
- This repo has no live workbook of its own — nothing here should be treated as a source of
  truth until it's actually built in SharePoint/Power Apps and confirmed against FRM10-12.
