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
- `sharepoint-lists/` — schema/export staging for new lists designed here (starting with
  **Order Items**), same convention as FRM10-12's `sharepoint-lists/`.

## Related repos
- `FRM09/` — Winding department workbook, depends on FRM10-12's `Orders` sheet via external
  references.
- `FRM10-12/` — the main planning/production workbook and source of truth; most of the
  underlying Power Query/SharePoint migration work happens there. This repo documents the
  system FRM10-12 is part of and stages the next list to migrate into it.

## Working notes
- Binary Office files here are tracked via **Git LFS** — see `.gitattributes`.
- This repo has no live workbook of its own — nothing here should be treated as a source of
  truth until it's actually built in SharePoint/Power Apps and confirmed against FRM10-12.
